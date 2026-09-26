"""Local extraction through Codex signed in with ChatGPT."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from contextlib import nullcontext

from .config import assets
from .models import Extraction
from .util import write_json


class CodexExtractor:
    def __init__(self, model: str, max_bytes: int, timeout: float = 180):
        self.executable = shutil.which('codex')
        if not self.executable:
            raise ValueError('Install Codex CLI and run codex login before using provider=codex')
        if max_bytes <= 0 or timeout <= 0:
            raise ValueError('Codex output size and timeout must be positive')
        self.model, self.max_bytes, self.timeout = model, max_bytes, timeout
        self.env = {k:v for k,v in os.environ.items()
                    if k not in {'OPENAI_API_KEY','CODEX_API_KEY','CODEX_ACCESS_TOKEN'}}

    def extract(self, text: str, document: dict, diagnostics: Path | None = None, *, contract=Extraction, prompt: str | None = None):
        from .extraction import strict_schema
        if diagnostics is not None:diagnostics.mkdir(parents=True,exist_ok=False)
        with (nullcontext(diagnostics) if diagnostics is not None else tempfile.TemporaryDirectory(prefix='epiweekly-extract-')) as directory:
            root = Path(directory).resolve()
            schema, output = root/'schema.json', root/'result.json'
            write_json(schema, strict_schema(contract.model_json_schema()))
            args = [self.executable, 'exec', '--ignore-user-config', '--ephemeral',
                    '--skip-git-repo-check', '--sandbox', 'read-only', '--json',
                    '--output-schema', str(schema), '--output-last-message', str(output)]
            for setting in ['forced_login_method="chatgpt"', 'model_provider="openai"',
                            'approval_policy="never"', 'web_search="disabled"',
                            'project_doc_max_bytes=0']:
                args.extend(['-c', setting])
            for feature in ['shell_tool','unified_exec','apps','plugins','hooks','multi_agent',
                            'browser_use','computer_use','image_generation','view_image',
                            'code_mode','code_mode_host','workspace_dependencies','skill_search',
                            'memories']:
                args.extend(['--disable', feature])
            if self.model:
                args.extend(['--model', self.model])
            args.append(assets('extract.md') if prompt is None else prompt)
            source = json.dumps({'document_title':document['title'],
                                 'publication_date':document['published_at'],
                                 'source_url':document['url'], 'captured_source_text':text})
            try:
                with (root/'events.jsonl').open('w+') as events, (root/'stderr.txt').open('w') as errors:
                    process = subprocess.run(args, input=source, text=True, cwd=root, env=self.env,
                                             stdout=events, stderr=errors, timeout=self.timeout)
                    events.seek(0)
                    completed = [json.loads(line) for line in events if line.strip()]
                failures=[e for e in completed if e.get('type') in {'turn.failed','error'}]
                if process.returncode or failures:
                    detail=json.dumps(failures[-1],ensure_ascii=False)[:1000] if failures else f'exit code {process.returncode}; inspect stderr.txt'
                    raise ValueError('Codex extraction failed: '+detail)
                turns = [e for e in completed if e.get('type')=='turn.completed']
                if not turns or any(e.get('type') in {'turn.failed','error'} for e in completed):
                    raise ValueError('Codex did not complete extraction')
                if not output.is_file() or output.stat().st_size > self.max_bytes:
                    raise ValueError('Codex output is missing or exceeds the configured byte limit')
                result = contract.model_validate_json(output.read_text())
            except subprocess.TimeoutExpired as exc:
                raise ValueError('Codex extraction exceeded its time limit') from exc
            except OSError as exc:
                raise ValueError('Codex extraction could not read or write its temporary files') from exc
            return result, {'provider':'codex', 'requested_model':self.model or None,
                            'authentication':'chatgpt', 'status':'completed',
                            'usage':[e.get('usage',{}) for e in turns]}

    def close(self):
        pass
