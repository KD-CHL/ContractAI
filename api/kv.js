// GitHub 仓库存储 —— 通过 Contents API 把数据 JSON 存进私有仓库
// 并发策略：sha 冲突时重新拉取再重试一次（最后写入者胜）
const OWNER = process.env.GITHUB_DATA_OWNER || 'KD-CHL';
const REPO = process.env.GITHUB_DATA_REPO || 'contractai-data';
const BRANCH = 'main';
const API_BASE = 'https://api.github.com';

const shaCache = new Map();

function authHeaders() {
  return {
    Authorization: 'Bearer ' + process.env.GITHUB_DATA_TOKEN,
    'Content-Type': 'application/json',
    'User-Agent': 'contractai-vercel',
  };
}

function fileOf(key) {
  return encodeURIComponent(key.replace(/:/g, '-')) + '.json';
}

function apiUrl(key) {
  return `${API_BASE}/repos/${OWNER}/${REPO}/contents/${fileOf(key)}?ref=${BRANCH}`;
}

export async function kvGet(key) {
  const res = await fetch(apiUrl(key), { headers: authHeaders() });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error('GitHub store read failed (' + res.status + ')');
  const data = await res.json();
  shaCache.set(key, data.sha);
  return JSON.parse(Buffer.from(data.content || '', 'base64').toString('utf8'));
}

export async function kvSet(key, value) {
  const body = {
    message: 'chore(data): update ' + fileOf(key),
    content: Buffer.from(JSON.stringify(value)).toString('base64'),
    branch: BRANCH,
  };
  const cached = shaCache.get(key);
  if (cached) body.sha = cached;

  let res = await fetch(apiUrl(key), {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(body),
  });

  if (res.status === 422 || res.status === 409) {
    const cur = await fetch(apiUrl(key), { headers: authHeaders() });
    if (cur.ok) {
      const curData = await cur.json();
      body.sha = curData.sha;
      res = await fetch(apiUrl(key), {
        method: 'PUT',
        headers: authHeaders(),
        body: JSON.stringify(body),
      });
    }
  }
  if (!res.ok) throw new Error('GitHub store write failed (' + res.status + ')');
  const result = await res.json();
  if (result?.content?.sha) shaCache.set(key, result.content.sha);
}
