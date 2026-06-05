# coding:utf-8
'''
检测 GitHub Trending 项目的 star 数，超过阈值（默认 7000）时通过 Telegram 通知。

扫描范围：README.md + archived 目录中最近 3 个文件。
增量策略：只查询 star < 阈值 的项目；一旦突破阈值就标记 notified，之后不再监控。
状态保存：stars_state.json（与脚本同目录）。

用法：
    export TELEGRAM_BOT_TOKEN="123456:abc..."
    export TELEGRAM_CHAT_ID="123456789"
    python check_stars.py            # 正常运行：突破阈值时推送
    SEED_MODE=true python check_stars.py   # 首次种子运行：只记录状态，不推送

依赖：requests （已在 requirements.txt 中）
'''
import os
import re
import json
import time
import requests

# ---- 配置（也可用环境变量覆盖）----
THRESHOLD          = int(os.environ.get('STAR_THRESHOLD', '7000'))
RECENT_FILES       = int(os.environ.get('RECENT_FILES', '3'))     # 扫描最近 N 个归档文件
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID   = os.environ.get('TELEGRAM_CHAT_ID', '')
SEED_MODE          = os.environ.get('SEED_MODE', '') == 'true'
GITHUB_TOKEN       = os.environ.get('GITHUB_TOKEN', '')           # 可选，提高 API 额度

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, 'stars_state.json')
URL_RE     = re.compile(r'github\.com/([^/\s]+)/([^/\s)]+)')


def target_files():
    ''' README.md + archived 目录中最近 RECENT_FILES 个 .md 文件 '''
    files = [os.path.join(BASE_DIR, 'README.md')]
    archived_dir = os.path.join(BASE_DIR, 'archived')
    archived = sorted(f for f in os.listdir(archived_dir) if f.endswith('.md'))
    for f in archived[-RECENT_FILES:]:
        files.append(os.path.join(archived_dir, f))
    return files


def collect_repos():
    ''' 解析目标文件，返回去重后的 owner/repo 列表 '''
    repos = {}
    for file in target_files():
        with open(file, 'r', encoding='utf-8') as fp:
            for line in fp:
                if not line.startswith('* 【'):
                    continue
                m = URL_RE.search(line)
                if m:
                    repos['%s/%s' % (m.group(1), m.group(2))] = True
    return list(repos.keys())


def fetch_stars(repos):
    ''' GraphQL 别名批量查询 star 数，每批 100 个 '''
    if not repos:
        return {}
    result, BATCH = {}, 100
    headers = {'Authorization': 'bearer ' + GITHUB_TOKEN} if GITHUB_TOKEN else {}
    for i in range(0, len(repos), BATCH):
        batch, parts, mapping = repos[i:i + BATCH], [], {}
        for idx, full in enumerate(batch):
            owner, name = full.split('/', 1)
            alias = 'r%d' % idx
            mapping[alias] = full
            parts.append('%s: repository(owner: %s, name: %s) { stargazerCount }'
                         % (alias, json.dumps(owner), json.dumps(name)))
        r = requests.post('https://api.github.com/graphql',
                          json={'query': 'query {\n%s\n}' % '\n'.join(parts)},
                          headers=headers, timeout=30)
        data = (r.json().get('data') or {})
        for alias, full in mapping.items():
            node = data.get(alias)            # 已删除/改名仓库返回 None，自动跳过
            if node and node.get('stargazerCount') is not None:
                result[full] = node['stargazerCount']
        print('checked %d/%d' % (min(i + BATCH, len(repos)), len(repos)))
        time.sleep(1)
    return result


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)


def notify(items):
    ''' 推送到 Telegram；单条上限 4096，按块切分 '''
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        print('WARNING: 未配置 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID，跳过推送')
        return
    items.sort(key=lambda x: -x[1])
    header = u'\U0001F31F GitHub Trending 项目突破 %d star：' % THRESHOLD
    lines = [u'• [%s](https://github.com/%s) — %d ⭐' % (f, f, c) for f, c in items]
    chunks, cur = [], header
    for ln in lines:
        if len(cur) + len(ln) + 1 > 3500:
            chunks.append(cur); cur = ln
        else:
            cur += '\n' + ln
    chunks.append(cur)
    for text in chunks:
        resp = requests.post(
            'https://api.telegram.org/bot%s/sendMessage' % TELEGRAM_BOT_TOKEN,
            json={'chat_id': TELEGRAM_CHAT_ID, 'text': text,
                  'parse_mode': 'Markdown', 'disable_web_page_preview': True}, timeout=30)
        if resp.status_code != 200:
            print('Telegram 推送失败:', resp.status_code, resp.text)


def main():
    repos = collect_repos()
    state = load_state()
    # 只扫 star < 阈值 的：已 notified（突破阈值）的直接跳过，不再监控
    candidates = [r for r in repos if not state.get(r, {}).get('notified')]
    print('scanned files: %d, distinct repos: %d, to check: %d'
          % (RECENT_FILES + 1, len(repos), len(candidates)))
    stars = fetch_stars(candidates)
    newly, crossed = [], []
    for full, count in stars.items():
        entry = state.get(full, {})
        entry['stars'] = count
        if count >= THRESHOLD:
            entry['notified'] = True
            crossed.append((full, count))
            if not SEED_MODE:
                newly.append((full, count))
        state[full] = entry
    save_state(state)
    if SEED_MODE:
        print('seed mode: %d repo(s) already >= %d star (not notifying):'
              % (len(crossed), THRESHOLD))
        for full, count in sorted(crossed, key=lambda x: -x[1]):
            print('  %6d  %s' % (count, full))
    else:
        print('newly crossed %d star: %d' % (THRESHOLD, len(newly)))
        if newly:
            notify(newly)


if __name__ == '__main__':
    main()
