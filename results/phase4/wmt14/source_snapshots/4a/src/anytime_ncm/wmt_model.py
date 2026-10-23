"""Pinned WMT official helpers, learned-cascade reconstruction and isolated online hook."""
import ast
from pathlib import Path
import torch
from torch.nn import functional as F
from omegaconf import OmegaConf
from anytime_ncm.upstream_adapter import _import_upstream,reconstruct_prefixes
from anytime_ncm.online import build_generator,IncrementalLatent
from anytime_ncm.wmt_policy import Stability
LEVELS=(1,4,8,14,20,26,32,40,48,56,64)
class WmtModel:
    def __init__(self,root):
        upstream=root/"third_party/ncm";_import_upstream(upstream)
        from models.vqvae import VQVAE
        from models.next_concept import NextConceptTransformer
        from tokenization.hf_tokenizer import HFTokenizer
        from tokenization.vqvae_tokenizer import VQVAETokenizer
        from transformers import AutoTokenizer
        self.root=root;cfg=OmegaConf.load(root/"artifacts/wmt14/config.yaml")
        if OmegaConf.to_container(cfg)!=OmegaConf.to_container(OmegaConf.load(upstream/"config/eval/wmt14.yaml")):
            raise ValueError("Released/upstream WMT config differs.")
        local=str(root/"artifacts/wmt14/text_tokenizer")
        self.source_tokenizer=AutoTokenizer.from_pretrained(local,local_files_only=True)
        special=dict(cfg.tokenizer.pre_tokenizer.special_tokens)
        pretok=HFTokenizer(local,**special,local_files_only=True)
        self.tokenizer=VQVAETokenizer(pretok,VQVAE(**cfg.tokenizer.vqvae))
        state=torch.load(root/"artifacts/wmt14/tokenizer.pt",map_location="cpu",weights_only=False)
        self.tokenizer.vqvae.load_state_dict(state["model"],strict=True);del state
        self.tokenizer.vqvae.cuda().eval()
        self.net=NextConceptTransformer(vqvae_local=self.tokenizer.vqvae,config=cfg.model).cuda()
        state=torch.load(root/"artifacts/wmt14/generator.pt",map_location="cpu",weights_only=False)
        self.net.load_state_dict(state["model"],strict=True);del state;self.net.eval()
        self.vq=self.tokenizer.vqvae.vq
        if tuple(self.vq.levels)!=LEVELS or not self.net.predict_level0 or self.net.query_level0:raise ValueError("WMT level-zero/hierarchy changed.")
        self.generate,self.patch=build_generator(upstream)
        nodes=[n for n in ast.parse((upstream/"scripts/eval_shard.py").read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ("prefix","pick_tokens","dec","run")]
        if len(nodes)!=4:raise ValueError("Official helpers missing.")
        self.official=dict(torch=torch,tk=self.tokenizer,net=self.net,src_tok=self.source_tokenizer,
             P=96,EOS=pretok.eos_token_id,PAD=pretok.pad_token_id,CUT_AT_EOS=True,
             freq=0.,ADJ=None,ALLOW=None,mu=0.,temp=1.,top_k=1,top_p=0.,cfg=0.,RAW=[])
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(upstream/"scripts/eval_shard.py"),"exec"),self.official)
        self.pick=self.official["pick_tokens"];self.decode=self.official["dec"]
        self.kwargs=dict(temperature=1.,top_k=1,top_p=0.,cfg_scale=0.,cfg_null_eos=pretok.eos_token_id)
        if any(p.dtype!=torch.float32 for net in (self.net,self.tokenizer.vqvae) for p in net.parameters()):raise ValueError("Require float32.")
    @torch.no_grad()
    def codes(self,context,callback=None,maximum=None):
        if context.shape!=(1,96) or context.dtype!=torch.long:raise ValueError("Require one official 96-token prefix.")
        if maximum is not None and (type(maximum)is not int or not 1<=maximum<=11):raise ValueError("Invalid WMT maximum.")
        try:return self.generate(self.net,None,context,**self.kwargs,level_callback=callback,level_limit=maximum)
        finally:self.net._cfg=None
    @torch.no_grad()
    def request(self,source,spec):
        if any(m.training for net in (self.net,self.tokenizer.vqvae) for m in net.modules()):raise ValueError("All WMT models must be in eval mode.")
        prefix=self.official["prefix"](source)
        context=torch.tensor([prefix],device=next(self.net.parameters()).device,dtype=torch.long)
        latest={};trace=[];monitor=IncrementalLatent(self.vq)
        tracker=Stability(spec) if spec["kind"] in ("stability","guarded") else None
        def callback(level,codes):
            ids=self.pick(self.tokenizer.vqvae.decoder(monitor.snapshot(codes,level)))[0].cpu().tolist()
            text=self.decode(ids);stop,change=tracker.observe(level,ids,text)
            latest.update(ids=ids,text=text,level=level);trace.append({"level":level,"ids":ids,"text":text,"change":change})
            return stop
        callback.inspection_levels=frozenset(range(spec.get("minimum",11),12))
        kind=spec["kind"]
        if kind=="full":codes=self.net.generate(None,context,**self.kwargs)
        elif kind=="disabled":codes=self.codes(context)
        elif kind=="fixed":codes=self.codes(context,maximum=spec["depth"])
        else:codes=self.codes(context,callback=callback,maximum=11)
        depth=next(i for i in range(1,12) if sum(LEVELS[:i])==codes.shape[1])
        if not latest:
            latent=self.vq.idx_to_z_q(codes) if depth==11 else monitor.snapshot(codes,depth)
            ids=self.pick(self.tokenizer.vqvae.decoder(latent))[0].cpu().tolist()
            latest.update(ids=ids,text=self.decode(ids),level=depth)
        return {"prefix_ids":prefix,"ids":latest["ids"],"text":latest["text"],"exit_level":depth,
                "codes":codes,"trace":trace,"inspections":[x["level"] for x in trace]}

@torch.no_grad()
def independent_prefixes(vq,codes):
    total=torch.zeros(codes.shape[0],64,vq.embed_dim,device=codes.device)
    snapshots=[];offset=0
    residuals=list(vq.quant_resi)
    for i,length in enumerate(LEVELS):
        term=F.embedding(codes[:,offset:offset+length],vq.embeddings[i].weight).transpose(1,2)
        if i==0:
            for layer in vq.learned_up_l1:
                if isinstance(layer,torch.nn.ConvTranspose1d):
                    term=F.conv_transpose1d(term,layer.weight,layer.bias,layer.stride,layer.padding,layer.output_padding,layer.groups,layer.dilation)
                elif isinstance(layer,torch.nn.GroupNorm):
                    term=F.group_norm(term,layer.num_groups,layer.weight,layer.bias,layer.eps)
                else:raise ValueError("Unsupported independent L1 operation.")
        elif i<10:term=F.interpolate(term,size=64,mode="linear")
        layer=residuals[i];ratio=layer.resi_ratio
        term=term.contiguous()
        term=term*(1-ratio)+F.conv1d(term,layer.weight,layer.bias,layer.stride,layer.padding,layer.dilation,layer.groups)*ratio
        total.add_(term.transpose(1,2).contiguous());snapshots.append(total.clone());offset+=length
    return snapshots
