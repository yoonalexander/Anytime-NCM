"""Publish the user-authorized research snapshot and verify public asset downloads."""
import argparse,hashlib,json,mimetypes,subprocess,urllib.error,urllib.parse,urllib.request
from pathlib import Path
BASE='https://api.github.com/repos/yoonalexander/Anytime-NCM';TAG='research-v0.1.0'
class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        new=super().redirect_request(req,fp,code,msg,headers,newurl)
        if new and urllib.parse.urlparse(newurl).hostname!=urllib.parse.urlparse(req.full_url).hostname:new.remove_header('Authorization')
        return new
OPENER=urllib.request.build_opener(SafeRedirect)
def raw(url,token=None,method='GET',body=None,content_type=None,accept='application/vnd.github+json'):
    headers={'Accept':accept,'User-Agent':'Anytime-NCM-research-release','X-GitHub-Api-Version':'2026-03-10'}
    if token:headers['Authorization']='Bearer '+token
    if content_type:headers['Content-Type']=content_type
    return OPENER.open(urllib.request.Request(url,data=body,headers=headers,method=method),timeout=120).read()
def api(path,token=None,method='GET',value=None):return json.loads(raw(BASE+path,token,method,json.dumps(value).encode() if value is not None else None,'application/json' if value is not None else None))
def digest(data):return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--assets',type=Path,required=True);p.add_argument('--notes',type=Path,required=True);p.add_argument('--ci',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
    ci=json.loads(a.ci.read_text());assert ci['head_sha']==a.commit and ci['conclusion']=='success' and len(ci['jobs'])==6 and all(j['conclusion']=='success' for j in ci['jobs'])
    assert subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],text=True).split()[0]==a.commit
    subprocess.run(['git','diff','--exit-code'],check=True);subprocess.run(['git','diff','--cached','--exit-code'],check=True)
    paths={p.name:p for p in a.assets.iterdir() if p.is_file()};assert len(paths)==6 and 'SHA256SUMS' in paths
    expected={name:digest(p.read_bytes()) for name,p in paths.items()}
    for line in paths['SHA256SUMS'].read_text().splitlines():
        h,name=line.split('  ',1);assert expected[name]==h
    cred=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,check=True,timeout=30);values=dict(x.split('=',1) for x in cred.stdout.splitlines() if '=' in x);token=values.get('password')
    if not token:raise RuntimeError('GitHub credential unavailable; no credential contents logged')
    releases=api('/releases?per_page=100',token);existing=next((r for r in releases if r['tag_name']==TAG),None)
    if existing:
        if existing['target_commitish']!=a.commit:raise ValueError('Existing tag/release has another target; preserve it')
        release=existing
    else:release=api('/releases',token,'POST',dict(tag_name=TAG,target_commitish=a.commit,name='Anytime NCM research snapshot 0.1.0',body=a.notes.read_text(encoding='utf-8'),draft=True,prerelease=False))
    rid=release['id'];state_path=a.receipt.with_name('release-publication-state.json')
    state_path.write_text(json.dumps(dict(release_id=rid,tag=TAG,target=a.commit,existing_release_reused=existing is not None))+'\n',encoding='utf-8')
    remote={x['name']:x for x in api('/releases/'+str(rid)+'/assets',token)}
    for name,path in paths.items():
        if name not in remote:
            if not release['draft']:raise ValueError('Published release missing asset; do not mutate automatically')
            url='https://uploads.github.com/repos/yoonalexander/Anytime-NCM/releases/'+str(rid)+'/assets?name='+urllib.parse.quote(name)
            remote[name]=json.loads(raw(url,token,'POST',path.read_bytes(),mimetypes.guess_type(name)[0] or 'application/octet-stream'))
        data=raw(remote[name]['url'],token,accept='application/octet-stream')
        if digest(data)!=expected[name]:raise ValueError('Uploaded asset mismatch; preserve release and inspect')
        print('Verified draft asset: '+name,flush=True)
    if release['draft']:release=api('/releases/'+str(rid),token,'PATCH',dict(tag_name=TAG,draft=False,prerelease=False))
    public=api('/releases/tags/'+TAG);assert not public['draft'] and public['target_commitish']==a.commit;verified=[]
    for asset in public['assets']:
        name=asset['name'];data=raw(asset['browser_download_url'])
        if name not in expected or digest(data)!=expected[name] or len(data)!=paths[name].stat().st_size:raise ValueError('Public release download differs')
        verified.append(dict(name=name,bytes=len(data),sha256=digest(data),url=asset['browser_download_url'],anonymous_download_verified=True))
        print('Verified public download: '+name,flush=True)
    assert len(verified)==6
    report=dict(status='published_and_verified',release_url=public['html_url'],tag=TAG,target_commit=a.commit,assets=verified,public_checksums_verified=True,existing_releases_preserved=True,package_registry_published=False,paid_services_used=False,credentials_logged_or_saved=False)
    with a.receipt.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report))
if __name__=='__main__':main()
