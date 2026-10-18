"""Prepare a reversible shortcut edit from a private Home data snapshot, offline."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--input',type=Path,required=True,help='Private extracted Home data directory')
ap.add_argument('--output',type=Path,required=True)
ap.add_argument('--remove',action='append',required=True,help='Exact component ID, e.g. d/webapp@STORE_ID')
a=ap.parse_args()
for value in a.remove:
 if not re.fullmatch(r'[A-Za-z0-9_./@-]+',value):raise SystemExit('Invalid component ID')
if a.output.exists():raise SystemExit('Output already exists')
a.output.mkdir(parents=True,mode=0o700)
changes=[]
for prefix in ('.appLayerCache','.listofremovedbyuser'):
 found=False
 for suffix in ('.1','.2'):
  f=a.input/(prefix+suffix)
  if not f.exists():continue
  found=True
  lines=f.read_text().splitlines()
  if len(lines)<3 or not lines[0].isdigit() or lines[-1]!='EOFCOBA':raise SystemExit('Unrecognized cache framing: '+f.name)
  if prefix=='.appLayerCache':payload=[s for s in lines[1:-1] if s not in a.remove]
  else:
   value=json.loads('\n'.join(lines[1:-1]))
   if not isinstance(value,dict):raise SystemExit('Unrecognized removed-shortcuts map')
   value.update({s:True for s in a.remove});payload=[json.dumps(value,separators=(',',':'))]
  data=('\n'.join([str(int(lines[0])+1),*payload,'EOFCOBA'])+'\n').encode()
  (a.output/f.name).write_bytes(data)
  changes.append((f.name,hashlib.sha256(f.read_bytes()).hexdigest(),data))
 if not found:raise SystemExit('Missing cache family: '+prefix)
script=['#!/bin/sh','set -eu','data=/opt/usr/home/owner/apps_rw/com.samsung.tv.csfs/data',
 'pids=$(ps -eo pid,comm | awk \'$2 == "DN_sung.tv.csfs" {print $1}\')',
 '[ -n "$pids" ] || { echo HOME_NOT_RUNNING; exit 1; }',
 'kill -STOP $pids',"trap 'kill -CONT $pids 2>/dev/null || true' EXIT"]
for name,before,data in changes:
 script.append(f'[ "$(sha256sum "$data/{name}" | cut -d " " -f 1)" = {before} ] || {{ echo CACHE_CHANGED_ABORT; exit 1; }}')
for name,before,data in changes:
 script.append(f'printf %s {base64.b64encode(data).decode()} | base64 -d > "$data/{name}"')
script += ['sync','kill -CONT $pids','trap - EXIT','echo SHORTCUTS_UPDATED_RESTART_HOME_WITH_SDK']
(a.output/'apply.sh').write_text('\n'.join(script)+'\n')
(a.output/'changes.json').write_text(json.dumps({'removed':a.remove,'files':[n for n,_,_ in changes]},indent=2)+'\n')
print('Prepared private edit:',a.output,'Input hashes will be checked again before writing.')
