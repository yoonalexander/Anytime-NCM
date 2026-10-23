"""Pin/download WMT14 assets and freeze effective-prefix identities; no NCM inference."""
from pathlib import Path
import sys,json,urllib.request,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from anytime_ncm.phase2 import save
from anytime_ncm.wmt_data import StringRows,make_manifest
MODEL="d342ce8aaea58830eef3b8ad473664673e41f692"
DATA="6580ba41a4b0a976dde876fbe84d25327617b0e6"
TOKEN="c1899de289a04d12100db370d81485cdf75e47ca"
def request(url):return json.load(urllib.request.urlopen(url,timeout=120))
def main():
    out=ROOT/"results/phase4/wmt14";out.mkdir(parents=True,exist_ok=True)
    inventory_path=ROOT/"configs/phase4_wmt_sources.json"
    if not inventory_path.exists():
        files={}
        for kind,repo,revision,sub,dest in (("models","hazyresearch/ncm-checkpoints",MODEL,"wmt14","artifacts/wmt14"),
            ("datasets","hazyresearch/ncm-datasets",DATA,"wmt14","data/wmt14"),
            ("models","Qwen/Qwen3-0.6B",TOKEN,"","artifacts/wmt14/text_tokenizer")):
            suffix="/"+sub if sub else ""
            rows=request(f"https://huggingface.co/api/{kind}/{repo}/tree/{revision}{suffix}?expand=true")
            allow={"config.yaml","generator.pt","tokenizer.pt"} if sub and kind=="models" else (
                {"sources.pickle","reference_translations.pickle"} if kind=="datasets" else
                {"config.json","tokenizer.json","tokenizer_config.json","vocab.json","merges.txt"})
            for r in rows:
                filename=r["path"].split("/")[-1]
                if filename not in allow:continue
                base="https://huggingface.co/"+("datasets/" if kind=="datasets" else "")+repo
                files[dest+"/"+filename]={"url":base+"/resolve/"+revision+"/"+r["path"],
                    "size":r["size"],"git_oid":r["oid"],"lfs_sha256":(r.get("lfs") or {}).get("oid")}
        if len(files)!=10:raise ValueError("Expected only five task assets and five tokenizer files.")
        save(inventory_path,{"task":"wmt14","model_revision":MODEL,"dataset_revision":DATA,"text_tokenizer_revision":TOKEN,"files":files})
    inventory=json.loads(inventory_path.read_text())
    preflight={"status":"downloading","declared_bytes":sum(r["size"] for r in inventory["files"].values()),
               "free_disk_bytes":shutil.disk_usage(ROOT).free,"NCM_model_calls":0}
    prior_path=out/"preflight.json"
    prior=json.loads(prior_path.read_text()) if prior_path.exists() else None
    completed_prior=prior is not None and prior.get("status")=="complete"
    if not completed_prior:save(prior_path,preflight)
    for name,r in inventory["files"].items():
        path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            print("Downloading",name,r["size"],flush=True)
            temporary=path.with_name(path.name+".download")
            with urllib.request.urlopen(r["url"],timeout=180) as remote,temporary.open("wb") as local:
                shutil.copyfileobj(remote,local,4*1024*1024)
            temporary.replace(path)
        size=path.stat().st_size
        if size!=r["size"]:raise ValueError("Download size mismatch: "+name)
        data=path.read_bytes();h=hashlib.sha256(data).hexdigest()
        if r["lfs_sha256"]:
            if h!=r["lfs_sha256"]:raise ValueError("LFS hash differs: "+name)
        elif hashlib.sha1(b"blob "+str(size).encode()+b"\0"+data).hexdigest()!=r["git_oid"]:
            raise ValueError("Git object hash differs: "+name)
        r["sha256"]=h
    save(inventory_path,inventory)
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(ROOT/"artifacts/wmt14/text_tokenizer",local_files_only=True)
    source=StringRows((ROOT/"data/wmt14/sources.pickle").read_bytes()).select(set(range(3003)))
    manifest=make_manifest([source[i] for i in range(3003)],tok)
    if manifest["unique_effective_prefix_groups"]<1024:raise ValueError("Insufficient groups for frozen allocation.")
    manifest_path=ROOT/"docs/partitions/wmt14-phase4.json"
    if manifest_path.exists():
        if json.loads(manifest_path.read_text())!=manifest:raise ValueError("Existing manifest differs.")
    else:save(manifest_path,manifest)
    lengths=[len(tok(source[i])["input_ids"]) for i in range(3003)]
    preflight.update(status="complete",manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
         inventory_sha256=hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
         source_rows=3003,effective_groups=manifest["unique_effective_prefix_groups"],reference_rows_materialized=0,
         source_token_lengths={"minimum":min(lengths),"maximum":max(lengths),"mean":sum(lengths)/len(lengths),
                              "truncated_at_96":sum(n>96 for n in lengths)},
         downloads_sha256={n:r["sha256"] for n,r in inventory["files"].items()})
    if not completed_prior:save(prior_path,preflight)
    else:
        for key in ("manifest_sha256","inventory_sha256","source_rows","effective_groups","downloads_sha256","source_token_lengths"):
            if prior[key]!=preflight[key]:raise ValueError("Completed preflight differs: "+key)
    print("Prepared WMT14; groups",manifest["unique_effective_prefix_groups"],"no references or NCM outputs inspected.",flush=True)
if __name__=="__main__":main()
