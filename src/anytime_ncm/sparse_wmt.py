"""Frozen sparse-observation assigned exits; no policy or reference inputs."""
import torch
from anytime_ncm.online import IncrementalLatent

@torch.no_grad()
def sparse_request(model, source, depth, schedule=(8, 10, 11)):
    if (type(depth) is not int or type(schedule) is not tuple
            or schedule != (8, 10, 11) or depth not in schedule):
        raise ValueError('Require frozen sparse schedule and an assigned exit in it')
    if any(m.training for net in (model.net, model.tokenizer.vqvae) for m in net.modules()):
        raise ValueError('Require all models in eval mode')
    prefix = model.official['prefix'](source)
    context = torch.tensor([prefix], dtype=torch.long, device=next(model.net.parameters()).device)
    monitor = IncrementalLatent(model.vq)
    observations = []
    def observe(level, codes):
        ids = model.pick(model.tokenizer.vqvae.decoder(monitor.snapshot(codes, level)))[0].cpu().tolist()
        observations.append(dict(level=level, ids=ids, text=model.decode(ids)))
        return False
    observe.inspection_levels = frozenset(d for d in schedule if d <= depth)
    codes = model.codes(context, callback=observe, maximum=depth)
    if codes.shape != (1, sum(model.vq.levels[:depth])) or [o['level'] for o in observations] != sorted(observe.inspection_levels):
        raise ValueError('Sparse forced boundary/observation mismatch')
    return dict(prefix_ids=prefix, codes=codes, exit_level=depth, observations=observations,
                ids=observations[-1]['ids'], text=observations[-1]['text'])
