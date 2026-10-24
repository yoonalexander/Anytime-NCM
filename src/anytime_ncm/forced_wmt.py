"""Forced WMT exits for E1. No reference, future-output or identity inputs."""
import torch
from anytime_ncm.online import IncrementalLatent


@torch.no_grad()
def forced_request(model, source, depth, schedule):
    if type(depth) is not int or not 1 <= depth <= 11 or schedule not in ('terminal', 'every_level'):
        raise ValueError('Invalid forced depth/schedule')
    if any(m.training for net in (model.net, model.tokenizer.vqvae) for m in net.modules()):
        raise ValueError('Require all models in eval mode')
    prefix = model.official['prefix'](source)
    context = torch.tensor([prefix], dtype=torch.long, device=next(model.net.parameters()).device)
    monitor = IncrementalLatent(model.vq)
    observations = []

    def observe(level, codes):
        ids = model.pick(model.tokenizer.vqvae.decoder(monitor.snapshot(codes, level)))[0].cpu().tolist()
        observations.append({'level': level, 'ids': ids, 'text': model.decode(ids)})
        return False

    observe.inspection_levels = frozenset(range(1, depth + 1))
    if schedule == 'every_level':
        codes = model.codes(context, callback=observe, maximum=depth)
    elif depth == 11:
        codes = model.net.generate(None, context, **model.kwargs)
    else:
        codes = model.codes(context, maximum=depth)
    if codes.shape != (1, sum(model.vq.levels[:depth])):
        raise ValueError('Forced boundary returned wrong code length')
    if not observations:
        latent = model.vq.idx_to_z_q(codes) if depth == 11 else monitor.snapshot(codes, depth)
        ids = model.pick(model.tokenizer.vqvae.decoder(latent))[0].cpu().tolist()
        observations.append({'level': depth, 'ids': ids, 'text': model.decode(ids)})
    return {'prefix_ids': prefix, 'codes': codes, 'exit_level': depth,
            'observations': observations, 'ids': observations[-1]['ids'], 'text': observations[-1]['text']}


class ForwardCounter:
    def __init__(self, model, limits):
        self.limits = dict(limits)
        self.counts = dict.fromkeys(limits, 0)
        self.calls = dict(generator_levels=0, decoder=0, encoder=0)
        self.handles = []
        for module, key in ((model.net.transformer.blocks[0], 'generator_levels'),
                            (model.tokenizer.vqvae.decoder, 'decoder'),
                            (model.tokenizer.vqvae.encoder, 'encoder')):
            self.handles.append(module.register_forward_pre_hook(lambda m, args, k=key: self.forward(k, args[0].shape[0])))

    def take(self, key, amount=1):
        if self.counts[key] + amount > self.limits[key]:
            raise RuntimeError('E1 forward/request allocation exhausted: ' + key)
        self.counts[key] += amount

    def forward(self, key, amount):
        self.take(key, amount)
        self.calls[key] += 1

    def close(self):
        for handle in self.handles:
            handle.remove()
        self.handles.clear()
