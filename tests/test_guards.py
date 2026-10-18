import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from tizen_dock import cli

class Guards(unittest.TestCase):
    def backup(self,directory):
        (directory/'snapshot.tar.gz').write_bytes(b'private synthetic snapshot')
        (directory/'manifest.json').write_text(json.dumps({'archive':'snapshot.tar.gz','sha256':cli.sha(directory/'snapshot.tar.gz'),'profile':cli.sha(cli.PROFILE)}))

    def test_backup_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);self.backup(d);cli.verify_backup(d)
            (d/'snapshot.tar.gz').write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError,'checksum'):cli.verify_backup(d)

    def test_backup_archive_cannot_escape_its_directory(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);self.backup(d)
            m=json.loads((d/'manifest.json').read_text());m['archive']='../snapshot.tar.gz'
            (d/'manifest.json').write_text(json.dumps(m))
            with self.assertRaises(ValueError):cli.verify_backup(d)

    def test_changed_build_never_contacts_tv(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);self.backup(d)
            (d/'test.dll').write_bytes(b'changed')
            (d/'manifest.json.build').write_text('')
            b=d/'build';b.mkdir();(b/'test.dll').write_bytes(b'changed')
            (b/'manifest.json').write_text(json.dumps({'profile_sha256':cli.sha(cli.PROFILE),'files':{'test.dll':'0'*64}}))
            with patch.object(cli,'adapter') as adapter:
                with self.assertRaisesRegex(ValueError,'Build file mismatch'):cli.apply({},b,d)
                adapter.assert_not_called()

    def test_invalid_app_id_never_runs_command(self):
        with patch.object(cli,'root') as root:
            with self.assertRaises(ValueError):cli.app_change({},'app; command',False)
            root.assert_not_called()

    def test_interrupted_app_change_retains_original_state(self):
        with tempfile.TemporaryDirectory() as t, patch.object(cli,'ROOT',Path(t)), patch.object(cli,'root',side_effect=['false\n',RuntimeError('interrupted')]):
            with self.assertRaises(RuntimeError):cli.app_change({},'example.App',False)
            records=list((Path(t)/'.local/changes').glob('*.json'))
            self.assertEqual(len(records),1)
            record=json.loads(records[0].read_text())
            self.assertEqual(record['before'],'false');self.assertFalse(record['complete'])

    def test_cache_edit_preserves_other_shortcuts_and_generations(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);source=d/'in';source.mkdir();out=d/'out'
            (source/'.appLayerCache.1').write_text('7\nd/webapp@KEEP\nd/webapp@REMOVE\nEOFCOBA\n')
            (source/'.listofremovedbyuser.1').write_text('2\n{"d/webapp@KEEP":false}\nEOFCOBA\n')
            subprocess.run([sys.executable,str(ROOT/'scripts/edit-home-cache.py'),'--input',str(source),'--output',str(out),'--remove','d/webapp@REMOVE'],check=True,capture_output=True)
            self.assertEqual((out/'.appLayerCache.1').read_text(),'8\nd/webapp@KEEP\nEOFCOBA\n')
            lines=(out/'.listofremovedbyuser.1').read_text().splitlines()
            self.assertEqual(lines[0],'3');self.assertEqual(json.loads(lines[1]),{'d/webapp@KEEP':False,'d/webapp@REMOVE':True})
            self.assertIn(cli.sha(source/'.appLayerCache.1'),(out/'apply.sh').read_text())

    def test_unknown_original_stops_before_build(self):
        spec=importlib.util.spec_from_file_location('build_overlays',ROOT/'scripts/build-overlays.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as t:
            d=Path(t);(d/'CompHome.dll').write_bytes(b'unknown firmware')
            with patch.object(module.subprocess,'run') as run:
                with self.assertRaisesRegex(ValueError,'mismatch'):module.build(d,d/'out')
                run.assert_not_called();self.assertFalse((d/'out').exists())

if __name__=='__main__':unittest.main()
