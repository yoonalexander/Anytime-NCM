"""Recorded-trajectory viewer: standard library only; no inference or fitting."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import math
import re
import statistics

from .dataset import _TokenRows, puzzle_identity, sha256
from .sudoku import parse_board
from .wmt_data import StringRows
from .wmt_policy import diagnostics, simulate

OUT = Path("results/phase5")
STUDIES = {
    "hard": ("Hard Sudoku · Phase 1", "results/phase1/trajectories.jsonl",
             "data/sudoku/hard", "results/phase1/summary.md"),
    "easy": ("Easy Sudoku · R3 / Phase 3", "results/followup/sudoku_easy_r3/trajectories.jsonl",
             "data/sudoku/easy", "results/phase3/summary.md"),
    "wmt14": ("WMT14 · German → English", "results/phase4/wmt14/trajectories.jsonl",
              "data/wmt14", "results/phase4/wmt14/summary.md"),
}
CF_RUN = "20261021T015457393177Z-probes"
CF_COLLECTION = "20261021T015216719695Z-collection"
CF_FAMILIES = ("input_decoded", "input_decoded_latent")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def dump(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":"), sort_keys=True)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(puzzle):
    """CF hashes 81 clue digits; Anytime hashes the original 91-token list."""
    return "".join(map(str, parse_board(puzzle).cells))


def cf_identity(puzzle):
    return hashlib.sha256(canonical(puzzle).encode("ascii")).hexdigest()


def sudoku_level(state, puzzle, reference):
    try:
        cells = parse_board(state["decoded_ids"]).cells
        clues = parse_board(puzzle).cells
        target = parse_board(reference).cells
        units = [cells[i:i+9] for i in range(0, 81, 9)]
        units += [cells[i::9] for i in range(9)]
        units += [tuple(cells[(r+a)*9+c+b] for a in range(3) for b in range(3))
                  for r in (0,3,6) for c in (0,3,6)]
        issues = {"blank cells": cells.count(0),
                  "clue violations": sum(bool(c) and c != v for c,v in zip(clues,cells)),
                  "invalid row/column/box units": sum(set(u) != set(range(1,10)) for u in units)}
        wrong = sum(a != b for a,b in zip(cells,target))
    except ValueError:
        issues, wrong = {"malformed output": 1}, None
    return {"level": state["level"], "text": state["decoded_text"],
            "valid": state["correctness"]["is_valid_solution"], "issues": issues,
            "offline": {"wrong reference cells": wrong},
            "codes": state["code_ids"], "continuation_value": None}


def policy_request(group, record):
    """All repetitions belong to the same identity/method; no pooled substitute."""
    group = sorted(group, key=lambda r:r["repeat"])
    require([r["repeat"] for r in group] == [0,1,2], "Missing/duplicate timing repeats.")
    first = group[0]
    depth = first["exit_level"]
    expected = record["levels"][depth-1]
    for row in group:
        text = row.get("decoded_text", row.get("text"))
        require(row["exit_level"] == depth and text == expected["text"], "Online/audit output differs.")
        require(math.isfinite(row["wall_ms"]) and row["wall_ms"] > 0, "Invalid request timing.")
        codes = row.get("generated_codes", row.get("codes"))
        if codes is not None:
            require(codes == [c for s in record["levels"][:depth] for c in s["codes"]], "Online/audit codes differ.")
    probabilities = {str(t["level"]): t["probability"] for t in first.get("learned_trace", [])}
    for value in probabilities.values():
        require(type(value) in (float,int) and math.isfinite(value) and 0 <= value <= 1, "Invalid sufficiency score.")
    require(all({str(t["level"]): t["probability"] for t in r.get("learned_trace", [])} == probabilities
                for r in group), "Sufficiency scores differ across repeats.")
    return {"exit": depth, "inspections": first.get("inspected_levels", first.get("inspections", [])),
            "cost_kind": "measured online development request", "wall_ms": [r["wall_ms"] for r in group],
            "mean_ms": statistics.mean(r["wall_ms"] for r in group),
            "sufficiency_probability": probabilities, "trace_repeat0": first.get("learned_trace", first.get("trace", []))}


def exact_cf_state(sample, level, cf_row):
    """A task/identity match alone is insufficient across batch/config boundaries."""
    return (cf_row["available_feature_version"] == "sudoku-full-prefix-v2"
            and cf_row["puzzle_id"] == sample["cf_identity"]
            and cf_row["level"] == level["level"]
            and cf_row["predicted_board"] == level["text"]
            and cf_row["codes_prefix"] == [s["codes"] for s in sample["levels"][:level["level"]]])


def checked_probabilities(document):
    ids = document["puzzle_ids"]
    require(len(ids) == len(set(ids)), "Duplicate CF prediction identity.")
    result = {}
    for family in CF_FAMILIES:
        values = document["probabilities"][family]
        require(len(values) == len(ids), "CF probability coverage differs.")
        require(all(type(p) in (int,float) and math.isfinite(p) and 0 <= p <= 1 for p in values),
                "Invalid CF failure probability.")
        result[family] = dict(zip(ids, values))
    return result


def firewall_bridge(root, cf_root, hard_samples):
    export = {"schema_version": 1, "target": "eventual invalid hard-Sudoku output",
              "families": list(CF_FAMILIES), "producer_run": CF_RUN, "forecasts": {},
              "external_sources": {}, "new_model_calls": 0, "benefit_claim": False,
              "limitation": "Saved CF internal-test forecasts only. No online, intervention, speedup or safety benefit established."}
    if cf_root is None:
        export.update(status="unavailable", reason="No Concept Firewall checkout supplied.")
        return export
    cf_root = Path(cf_root)
    def external(name):
        path = cf_root/name
        export["external_sources"][name] = sha256(path)
        return path
    producer = read(external("results/manifests/"+CF_RUN+".json"))
    collection = read(external("results/manifests/"+CF_COLLECTION+".json"))
    require(producer["collection_sha256"] == sha256(cf_root/"results/manifests"/(CF_COLLECTION+".json")),
            "CF collection provenance differs.")
    require(producer["status"] == "passed" and collection["status"] == "passed", "Incomplete CF producer.")
    ncm = read(root/"results/phase1/trajectories.metadata.json")
    for name in ("generator.pt", "tokenizer.pt"):
        expected = next(r["sha256"] for r in ncm["checkpoint_artifacts"] if r["path"].endswith("/"+name))
        require(collection["artifact_sha256"]["artifacts/sudoku-hard/"+name] == expected, "CF checkpoint mismatch.")
    require(producer["upstream_commit"] == ncm["sources"]["upstream_commit"], "CF upstream mismatch.")
    for name in ("schema.py","probes.py","representations.py"):
        external("src/concept_firewall/"+name)
    external("results/reports/probe_evaluation.md")
    sample_by_cf = {r["cf_identity"]:r for r in hard_samples}
    require(len(sample_by_cf) == len(hard_samples), "Canonical puzzle collision.")
    forecasts = {}
    for level in range(1,13):
        path = external("results/probes/"+CF_RUN+f"/level-{level:02d}-test_predictions.json")
        # Outcome arrays are not decision inputs and are not decoded/exported.
        raw, count = re.subn(r'("failure"\s*:\s*)\[[^\]]*\]', r'\1[]', path.read_text(encoding="utf-8"))
        require(count == 1, "Unexpected CF prediction grammar.")
        table = checked_probabilities(json.loads(raw))
        for key in set(table[CF_FAMILIES[0]]) & sample_by_cf.keys():
            forecasts[key,level] = {f:table[f][key] for f in CF_FAMILIES}
    path = external("results/trajectories/"+CF_COLLECTION+"/levels.jsonl")
    matched, rejected, seen = 0, 0, set()
    # Skip unused CF state bodies, including their label/feature operands.
    pattern = re.compile(r'"puzzle_id"\s*:\s*"([0-9a-f]{64})"')
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            found = pattern.search(line)
            if not found or found[1] not in sample_by_cf:
                continue
            row = json.loads(line);key = (row["puzzle_id"], row["level"])
            if key not in forecasts:
                continue
            require(key not in seen, "Duplicate CF observed state.");seen.add(key)
            sample = sample_by_cf[key[0]]
            if not exact_cf_state(sample, sample["levels"][key[1]-1], row):
                rejected += 1
                continue
            export["forecasts"].setdefault(sample["identity"], {})[str(key[1])] = forecasts[key]
            matched += 1
    require(seen == set(forecasts), "Missing CF observed states for saved forecasts.")
    export.update(status="complete", candidate_states=len(forecasts), matched_states=matched,
                  mismatched_states=rejected, matched_puzzles=len(export["forecasts"]),
                  checkpoint_hashes_match=True, producer_collection_batch=8,
                  identity_conversion="SHA256 of canonical 81 clue digits; not the Anytime token-list hash",
                  level12="post-generation diagnosis only",
                  primary_result="Producer level-6 latent increment AUROC -0.0078; 95% interval [-0.0368, +0.0193]. No demonstrated benefit.")
    return export

def build(root, cf_root=None):
    root = Path(root);sources = {}
    def source(name, expected=None):
        path = root/name;digest = sha256(path)
        require(expected is None or expected == digest, "Recorded input digest differs: "+str(name))
        sources[str(name).replace("\\","/")] = digest
        return path
    studies = []
    for key,(label,trajectory,dataset,report) in STUDIES.items():
        if key == "hard":
            meta = read(source("results/phase1/trajectories.metadata.json"))
            expected = meta["trajectory_sha256"]
            pins = {p["path"]:p["sha256"] for p in meta["checkpoint_artifacts"]}
            manifest_name = "docs/partitions/sudoku-hard.json"
        elif key == "easy":
            meta = read(source("results/followup/sudoku_easy_r3/collection.json"))
            expected = meta["artifacts_sha256"]["trajectories.jsonl"]
            pins = meta["inputs_sha256"]
            manifest_name = "docs/partitions/sudoku-easy-r2.json"
        else:
            meta = read(source("results/phase4/wmt14/4a.json"))
            expected = meta["artifacts_sha256"]["trajectories.jsonl"]
            pins = meta["inputs_sha256"]
            manifest_name = "docs/partitions/wmt14-phase4.json"
        records = list(rows(source(trajectory, expected)))
        count = 192 if key == "wmt14" else 1400
        require(len(records) == count, "Incomplete viewer trajectory coverage.")
        manifest = read(source(manifest_name))
        allowed = {e["index"]:e for part in ("exploration","development") for e in manifest["partitions"][part]}
        indices = {r["index" if key == "wmt14" else "dataset_index"] for r in records}
        require(len(indices) == count and indices <= allowed.keys(), "Viewer partition/index differs.")
        if key == "wmt14":
            a = StringRows(source(dataset+"/sources.pickle", pins[dataset+"/sources.pickle"]).read_bytes()).select(indices)
            b = StringRows(source(dataset+"/reference_translations.pickle", pins[dataset+"/reference_translations.pickle"]).read_bytes()).select(indices)
        else:
            a = _TokenRows(source(dataset+"/puzzles.pickle", pins[dataset+"/puzzles.pickle"]).read_bytes()).select(indices,91,2000)
            b = _TokenRows(source(dataset+"/solutions.pickle", pins[dataset+"/solutions.pickle"]).read_bytes()).select(indices,89,2000)
        provenance = {"collection":{k:meta[k] for k in ("run_id","stage","base_commit","started_utc","finished_utc",
            "sources","execution","timing","source_snapshot","checkpoint_artifacts","inputs_sha256",
            "protocol_sha256","config_sha256","batch_size") if k in meta}}
        samples = []
        for row in records:
            index = row["index" if key == "wmt14" else "dataset_index"]
            ident = row["identity" if key == "wmt14" else "sample_id"]
            expected_id = allowed[index]["identity" if key == "wmt14" else "puzzle_sha256"]
            require(ident == expected_id and row["partition"] in ("exploration","development"), "Viewer identity differs.")
            require([s["level"] for s in row["levels"]] == list(range(1,12 if key=="wmt14" else 13)), "Missing recorded levels.")
            if key == "wmt14":
                lengths = (1,4,8,14,20,26,32,40,48,56,64)
                levels = [{"level":s["level"],"text":s["text"],"valid":None,
                           "codes":row["codes"][sum(lengths[:s["level"]-1]):sum(lengths[:s["level"]])],
                           "issues":{"digit-number cues":diagnostics(s["text"], b[index])["number_cues"],
                                     "negation cue":diagnostics(s["text"], b[index])["negation_cue"]},
                           "offline":{k:v for k,v in diagnostics(s["text"],b[index]).items()
                                      if k in ("numeric_reference_f1","negation_cue_mismatch")},
                           "continuation_value":None} for s in row["levels"]]
                text,reference = a[index],b[index]
            else:
                require(puzzle_identity(a[index]) == ident, "Viewer source puzzle identity differs.")
                levels = [sudoku_level(s,a[index],b[index]) for s in row["levels"]]
                text,reference = canonical(a[index]),canonical(b[index])
            sample = {"index":index,"identity":ident,"partition":row["partition"],
                      "source":text,"reference":reference,"levels":levels,"policies":{}}
            if key == "wmt14":
                sample["model_prefix_ids"] = row["prefix_ids"]
            if key == "hard":
                sample["cf_identity"] = cf_identity(a[index])
            samples.append(sample)
        samples.sort(key=lambda r:r["index"])
        policies = {"full":{"kind":"full","depth":len(samples[0]["levels"])}}
        if key == "wmt14":
            audit = read(source("results/phase4/wmt14/audit_analysis.json"))
            policies = audit["selection"]["methods"]
            for r,original in zip(sorted(samples,key=lambda s:s["index"]),sorted(records,key=lambda s:s["index"])):
                for name,spec in policies.items():
                    r["policies"][name] = {"exit":simulate(spec,original["levels"]),
                          "inspections":list(range(spec["minimum"],12)) if "minimum" in spec else [],
                          "cost_kind":"offline policy replay; request latency unavailable", "wall_ms":[],
                          "mean_ms":None,"sufficiency_probability":{}}
        else:
            policies["first_valid_replay"] = {"kind":"offline exact verifier","fallback":12}
            for r in samples:
                for name in policies:
                    exit_level = next((s["level"] for s in r["levels"] if s["valid"]),12) if name=="first_valid_replay" else 12
                    r["policies"][name] = {"exit":exit_level,"inspections":list(range(1,exit_level+1)) if name!="full" else [],
                        "cost_kind":"offline policy replay; request latency unavailable","wall_ms":[],
                        "mean_ms":None,"sufficiency_probability":{}}
        if key != "hard":
            name = "results/phase4/wmt14/4b.json" if key=="wmt14" else "results/phase3/3b.json"
            bench = read(source(name))
            provenance["online_development"] = {k:bench[k] for k in ("stage","started_utc","finished_utc",
                "execution","source_snapshot","inputs_sha256","source_sha256") if k in bench}
            logname = name.replace(".json","_requests.jsonl")
            log = list(rows(source(logname,bench["artifacts_sha256"][Path(logname).name])))
            policies.update(bench["methods"])
            grouped = defaultdict(list)
            for row in log:grouped[row.get("sample_id",row.get("identity")),row["method"]].append(row)
            by_id = {r["identity"]:r for r in samples}
            for (identity,method),group in grouped.items():
                require(identity in by_id, "Benchmark sample missing from audited set.")
                by_id[identity]["policies"][method] = policy_request(group,by_id[identity])
                by_id[identity]["policies"][method]["evidence"] = logname
        estimate = None
        if key in ("hard","easy"):
            name = "results/phase1/analysis.json" if key=="hard" else "results/followup/sudoku_easy_r3/analysis.json"
            analysis = read(source(name));v = analysis["calibration_sensitivity_costs"]["development"]
            estimate = {"kind":"development cohort component-sum estimate; not a per-input online measurement",
                        "full_mean_ms":v["baseline_ms"]["mean"],"every_level_mean_ms":v["verified_ms"]["mean"],
                        "evidence":name}
        studies.append({"id":key,"label":label,"report":report,"trajectory":trajectory,
                        "policies":policies,"estimated_cost":estimate,"samples":samples,"provenance":provenance})
    bridge = firewall_bridge(root, cf_root, studies[0]["samples"])
    for r in studies[0]["samples"]:
        r["firewall"] = bridge["forecasts"].get(r["identity"],{})
    for name in ("docs/phase5_scope.md","docs/phase5_firewall_contract.md",
                 "src/anytime_ncm/viewer.py","src/anytime_ncm/viewer.html","scripts/view_trajectories.py",
                 "tests/test_viewer.py"):
        source(name)
    payload = {"schema_version":1,"studies":studies,"sources":sources,
               "bridge":{k:v for k,v in bridge.items() if k not in ("forecasts","external_sources")},
               "claims":"Recorded exploration/development evidence. No new model calls, fits, retuning or safety benefit."}
    out = root/OUT;out.mkdir(parents=True,exist_ok=True)
    (out/"firewall_bridge.json").write_text(dump(bridge)+"\n",encoding="utf-8",newline="\n")
    template = (root/"src/anytime_ncm/viewer.html").read_text(encoding="utf-8")
    html = embed(template,payload)
    (out/"viewer.html").write_text(html,encoding="utf-8",newline="\n")
    catalog = {"schema_version":1,"studies":[{"id":s["id"],"count":len(s["samples"]),
               "levels":sum(len(r["levels"]) for r in s["samples"])} for s in studies],
               "bridge":payload["bridge"],"sources":sources}
    (out/"catalog.json").write_text(dump(catalog)+"\n",encoding="utf-8",newline="\n")
    manifest = {"status":"complete","sources":sources,"external_sources":bridge["external_sources"],
                "artifacts":{n:sha256(out/n) for n in ("viewer.html","catalog.json","firewall_bridge.json")},
                "new_model_calls":0,"new_fits":0,"final_inputs_materialized":0}
    (out/"build.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    return catalog


def embed(template, payload):
    require(template.count("<!--DATA-->") == 1, "Viewer data slot differs.")
    # HTML parsers recognize closing script tags even in JSON strings.
    encoded = dump(payload).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return template.replace("<!--DATA-->", '<script id="data" type="application/json">'+encoded+"</script>")


def verify(root, cf_root=None):
    root = Path(root);out = root/OUT;manifest = read(out/"build.json")
    for name,digest in manifest["sources"].items():
        require(sha256(root/name) == digest, "Viewer source changed: "+name)
    for name,digest in manifest["artifacts"].items():
        require(sha256(out/name) == digest, "Viewer artifact changed: "+name)
    if cf_root is not None:
        for name,digest in manifest["external_sources"].items():
            require(sha256(Path(cf_root)/name) == digest, "CF source changed: "+name)
    text = (out/"viewer.html").read_text(encoding="utf-8")
    match = re.search(r'<script id="data" type="application/json">(.*?)</script>',text,re.S)
    require(match is not None, "Missing embedded dataset.")
    data = json.loads(match[1]);catalog = read(out/"catalog.json");bridge = read(out/"firewall_bridge.json")
    require(data["sources"] == manifest["sources"] == catalog["sources"], "Viewer provenance differs.")
    require(data["bridge"] == catalog["bridge"] == {k:v for k,v in bridge.items() if k not in ("forecasts","external_sources")},
            "Viewer bridge metadata differs.")
    require([s["id"] for s in data["studies"]] == ["hard","easy","wmt14"], "Viewer studies differ.")
    for study,count in zip(data["studies"],(1400,1400,192)):
        key = study["id"];dataset = STUDIES[key][2]
        original = list(rows(root/study["trajectory"]))
        indexed = {r.get("sample_id",r.get("identity")):r for r in original}
        samples = study["samples"];indices = {r["index"] for r in samples}
        require(len(samples) == len(indices) == len(indexed) == count, "Viewer coverage differs.")
        if key=="wmt14":
            source = StringRows((root/dataset/"sources.pickle").read_bytes()).select(indices)
            reference = StringRows((root/dataset/"reference_translations.pickle").read_bytes()).select(indices)
            expected_specs = read(root/"results/phase4/wmt14/audit_analysis.json")["selection"]["methods"]
        else:
            source = _TokenRows((root/dataset/"puzzles.pickle").read_bytes()).select(indices,91,2000)
            reference = _TokenRows((root/dataset/"solutions.pickle").read_bytes()).select(indices,89,2000)
            expected_specs = {"full":{"kind":"full","depth":12},
                              "first_valid_replay":{"kind":"offline exact verifier","fallback":12}}
        measured = defaultdict(list)
        if key!="hard":
            name = "results/phase4/wmt14/4b.json" if key=="wmt14" else "results/phase3/3b.json"
            expected_specs.update(read(root/name)["methods"])
            logname = name.replace(".json","_requests.jsonl")
            for row in rows(root/logname):
                measured[row.get("sample_id",row.get("identity")),row["method"]].append(row)
        require(study["policies"]==expected_specs, "Viewer policy specification differs.")
        for sample in samples:
            row = indexed[sample["identity"]];index = sample["index"]
            require(sample["partition"] in ("exploration","development") and sample["partition"]==row["partition"],
                    "Final/wrong partition included.")
            require(index == row.get("dataset_index",row.get("index")), "Viewer row index differs.")
            require(sample["source"]==(source[index] if key=="wmt14" else canonical(source[index]))
                    and sample["reference"]==(reference[index] if key=="wmt14" else canonical(reference[index])),
                    "Viewer source/reference differs.")
            require(len(sample["levels"]) == len(row["levels"]), "Viewer level coverage differs.")
            for state,old in zip(sample["levels"],row["levels"]):
                require(state["text"] == old.get("decoded_text",old.get("text")) and state["level"]==old["level"],
                        "Viewer reconstruction differs.")
                require(state["continuation_value"] is None, "Invented continuation value.")
                if key!="wmt14":
                    require(state==sudoku_level(old,source[index],reference[index]), "Viewer Sudoku issues/codes differ.")
                else:
                    diag = diagnostics(old["text"],reference[index])
                    require(state["valid"] is None and state["issues"]=={"digit-number cues":diag["number_cues"],
                            "negation cue":diag["negation_cue"]} and state["offline"]=={k:diag[k] for k in
                            ("numeric_reference_f1","negation_cue_mismatch")}, "Viewer language diagnostics differ.")
                    require(sample["model_prefix_ids"]==row["prefix_ids"], "Viewer model input differs.")
                    lengths=(1,4,8,14,20,26,32,40,48,56,64);n=old["level"]
                    require(state["codes"]==row["codes"][sum(lengths[:n-1]):sum(lengths[:n])], "Viewer language codes differ.")
            available = set(expected_specs) if key=="wmt14" else {"full","first_valid_replay"}
            available |= {method for identity,method in measured if identity==sample["identity"]}
            require(set(sample["policies"])==available, "Viewer method availability differs.")
            for method,policy in sample["policies"].items():
                actual = measured.get((sample["identity"],method))
                if actual:
                    expected = policy_request(actual,sample);expected["evidence"]=logname
                    require(policy==expected, "Viewer measured timing/policy trace differs.")
                else:
                    depth = simulate(expected_specs[method],row["levels"]) if key=="wmt14" else (
                        next((s["level"] for s in row["levels"] if s["correctness"]["is_valid_solution"]),12)
                        if method=="first_valid_replay" else 12)
                    require(policy["exit"]==depth and policy["mean_ms"] is None and not policy["wall_ms"]
                            and not policy["sufficiency_probability"] and policy["cost_kind"].startswith("offline policy replay"),
                            "Viewer offline replay or unavailable timing differs.")
            if key=="hard":
                require(sample["cf_identity"]==cf_identity(source[index]) and sample["firewall"] ==
                        bridge["forecasts"].get(sample["identity"],{}), "Viewer risk identity/join differs.")
    if cf_root is not None:
        require(firewall_bridge(root,cf_root,data["studies"][0]["samples"])==bridge, "Recomputed CF bridge differs.")
    require(bridge["new_model_calls"]==0 and not bridge["benefit_claim"], "Unsupported bridge benefit claim.")
    return {"status":"verified","trajectories":2992,"levels":35712,"bridge_matched_states":bridge.get("matched_states",0)}
