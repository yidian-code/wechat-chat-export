#!/usr/bin/env python
"""Export selected Windows WeChat 4.x chats without persisting database keys."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'vendor'))
from wx4 import decrypt, export, key, paths
from wx4.reader import open_data


def relevant(rel):
    base = os.path.basename(rel).lower()
    return base in ('contact.db', 'session.db') or bool(re.fullmatch(r'message_\d*\.db', base))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('accounts')
    p = sub.add_parser('export')
    p.add_argument('--account', help='exact account directory name')
    p.add_argument('--chat', action='append', required=True, help='exact display name; repeatable')
    p.add_argument('--group-only', action='store_true')
    p.add_argument('--session', action='append', help='exact session identifier from --list; repeatable')
    p.add_argument('--all-matches', action='store_true', help='export every same-name match')
    p.add_argument('--list', action='store_true', help='list matched metadata without exporting')
    p.add_argument('--out', help='existing or new output directory')
    p.add_argument('--formats', nargs='+', choices=['json', 'csv', 'html'], default=['json', 'csv', 'html'])
    a = parser.parse_args()
    accounts = paths.list_account_dirs()
    if a.command == 'accounts':
        print(json.dumps([{'account': x['dir_name']} for x in accounts], ensure_ascii=False))
        return 0
    if not a.list and not a.out:
        parser.error('--out is required unless --list is used')
    if not accounts:
        raise RuntimeError('未找到微信账号数据目录。')
    selected = [x for x in accounts if x['dir_name'] == a.account] if a.account else accounts
    if len(selected) != 1:
        raise RuntimeError('存在多个账号或指定账号不存在；请通过 accounts 查看并使用 --account 精确选择。')
    account = selected[0]
    temp = Path(tempfile.mkdtemp(prefix='wechat-export-private-')).resolve()
    print('临时目录:', temp, flush=True)
    data = None
    try:
        ex = key.KeyExtractor(account['db_storage'], progress=lambda _: None)
        ex.extract()
        payload = ex.result_payload()
        expected = [item['rel'] for item in ex.db_files if relevant(item['rel'])]
        available = {rel: payload[rel] for rel in expected if rel in payload}
        missing = [rel for rel in expected if rel not in payload]
        if missing:
            print('警告：未取得密钥的数据库:', ', '.join(missing), flush=True)
        result = decrypt.decrypt_all(available, account['db_storage'], str(temp), progress=lambda _: None)
        for category in ('failed', 'skipped'):
            if result[category]:
                print('警告：数据库处理未完成:', category, result[category], flush=True)
        dbnames = {os.path.basename(rel).lower() for rel in result['ok']}
        if not {'contact.db', 'session.db'} <= dbnames or not any(re.fullmatch(r'message_\d*\.db', n) for n in dbnames):
            raise RuntimeError('缺少联系人、会话或消息数据库，无法可靠匹配会话。')
        data = open_data(str(temp), account['wxid'], account_dir=account['path'], progress=lambda _: None)
        sessions = data.sessions()
        errors = False
        for name in dict.fromkeys(a.chat):
            found = [s for s in sessions if s['display'] == name and (not a.group_only or s['is_group'])
                     and (not a.session or s['username'] in a.session)]
            if not found:
                print('未找到精确匹配:', name, flush=True)
                errors = True
                continue
            if len(found) > 1 and not (a.list or a.all_matches):
                print('同名会话有', len(found), '个；请先用 --list 核对，未导出:', name, flush=True)
                errors = True
                continue
            for index, session in enumerate(found, 1):
                messages = data.messages(session['username'])
                times = [m.get('time_str') for m in messages if m.get('time_str')]
                print(json.dumps({'name':name, 'index':index, 'session':session['username'],
                    'group':session['is_group'], 'count':len(messages),
                    'first':min(times) if times else None, 'last':max(times) if times else None}, ensure_ascii=False), flush=True)
                if a.list:
                    continue
                if not messages:
                    errors = True
                    continue
                out = Path(a.out).expanduser().resolve()
                out.mkdir(parents=True, exist_ok=True)
                label = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', name).strip(' .') or 'chat'
                suffix = f'_{index}' if len(found) > 1 else ''
                for fmt in dict.fromkeys(a.formats):
                    target = out / f'{label}{suffix}.{fmt}'
                    if target.exists():
                        raise FileExistsError(f'目标文件已存在，不覆盖: {target}')
                    getattr(export, 'export_' + fmt)(data, session['username'], str(target))
                    print('已导出:', target, flush=True)
        return 2 if errors or missing or result['failed'] or result['skipped'] else 0
    finally:
        if data is not None:
            data.close()
        if temp.name.startswith('wechat-export-private-') and temp.parent == Path(tempfile.gettempdir()).resolve():
            shutil.rmtree(temp)
            print('临时目录已清理', flush=True)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError) as exc:
        print('错误:', str(exc), file=sys.stderr)
        sys.exit(1)
