import { pool } from '../db/index.js';

function rowToSummary(row) {
  if (!row) return null;
  return {
    id: row.id,
    created_at: row.created_at,
    updated_at: row.updated_at,
    title: row.title,
    transcript: row.transcript,
    summary: row.summary,
    instruction: row.instruction,
    meeting_title: row.meeting_title,
    meeting_date: row.meeting_date,
    meeting_type: row.meeting_type,
    participants: row.participants ?? [],
    location: row.location,
    tags: row.tags ?? [],
    action_items: row.action_items ?? [],
    decisions: row.decisions ?? [],
    deadlines: row.deadlines ?? [],
    extracted_participants: row.extracted_participants ?? [],
    is_shared: row.is_shared ?? false,
    email_recipients: row.email_recipients ?? [],
    meeting_id: row.meeting_id ?? null,
  };
}

export async function saveSummary(input) {
  const {
    transcript,
    summary,
    instruction,
    title,
    meetingTitle,
    meetingDate,
    meetingType,
    participants = [],
    location,
    tags = [],
    actionItems = [],
    decisions = [],
    deadlines = [],
    extractedParticipants = [],
    meetingId,
    userId,
  } = input;

  const result = await pool.query(
    `INSERT INTO summaries (
      title, transcript, summary, instruction,
      meeting_title, meeting_date, meeting_type, participants, location, tags,
      action_items, decisions, deadlines, extracted_participants, meeting_id, user_id
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
    RETURNING id, created_at`,
    [
      title ?? null,
      transcript ?? null,
      summary,
      instruction ?? null,
      meetingTitle ?? null,
      meetingDate ?? null,
      meetingType ?? null,
      JSON.stringify(participants),
      location ?? null,
      JSON.stringify(tags),
      JSON.stringify(actionItems),
      JSON.stringify(decisions),
      JSON.stringify(deadlines),
      JSON.stringify(extractedParticipants),
      meetingId ?? null,
      userId,
    ]
  );

  const row = result.rows[0];
  return row ? { id: row.id, created_at: row.created_at } : null;
}

export async function listSummaries(options = {}, userId) {
  const {
    skip = 0,
    take = 20,
    search = '',
    dateFrom = null,
    dateTo = null,
    meetingType = null,
    meetingId = null,
    uploadOnly = false,
    tags = [],
    sortBy = 'created_at',
    sortOrder = 'desc',
  } = options;

  const params = [];
  const conditions = [];
  let idx = 1;

  if (userId) {
    conditions.push(`user_id = $${idx}`);
    params.push(userId);
    idx += 1;
  }

  if (meetingId) {
    conditions.push(`meeting_id = $${idx}`);
    params.push(meetingId);
    idx += 1;
  }
  if (uploadOnly) {
    conditions.push('meeting_id IS NULL');
  }
  if (search && search.trim()) {
    conditions.push(`(summary ILIKE $${idx} OR meeting_title ILIKE $${idx} OR title ILIKE $${idx})`);
    params.push(`%${search.trim()}%`);
    idx += 1;
  }
  if (dateFrom) {
    conditions.push(`meeting_date >= $${idx}`);
    params.push(dateFrom);
    idx += 1;
  }
  if (dateTo) {
    conditions.push(`meeting_date <= $${idx}`);
    params.push(dateTo);
    idx += 1;
  }
  if (meetingType) {
    conditions.push(`meeting_type = $${idx}`);
    params.push(meetingType);
    idx += 1;
  }
  if (Array.isArray(tags) && tags.length > 0) {
    conditions.push(`tags ?| $${idx}`);
    params.push(tags);
    idx += 1;
  }

  const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';
  const order = sortOrder === 'asc' ? 'ASC' : 'DESC';
  const validSort = ['created_at', 'updated_at', 'meeting_date', 'meeting_title'].includes(sortBy)
    ? sortBy
    : 'created_at';
  params.push(take, skip);
  const q = `SELECT * FROM summaries ${where} ORDER BY ${validSort} ${order} LIMIT $${idx} OFFSET $${idx + 1}`;
  const result = await pool.query(q, params);
  return result.rows.map(rowToSummary);
}

export async function getSummaryById(id, userId) {
  const result = await pool.query(
    'SELECT * FROM summaries WHERE id = $1 AND user_id = $2',
    [id, userId]
  );
  return rowToSummary(result.rows[0]);
}

export async function deleteSummary(id, userId) {
  const result = await pool.query(
    'DELETE FROM summaries WHERE id = $1 AND user_id = $2',
    [id, userId]
  );
  return (result.rowCount ?? 0) > 0;
}

const CAMEL_TO_SNAKE = {
  title: 'title',
  summary: 'summary',
  instruction: 'instruction',
  isShared: 'is_shared',
  emailRecipients: 'email_recipients',
  meetingTitle: 'meeting_title',
  meetingDate: 'meeting_date',
  meetingType: 'meeting_type',
  participants: 'participants',
  location: 'location',
  tags: 'tags',
  actionItems: 'action_items',
  decisions: 'decisions',
  deadlines: 'deadlines',
  extractedParticipants: 'extracted_participants',
};

export async function updateSummary(id, data, userId) {
  const updates = Object.keys(CAMEL_TO_SNAKE)
    .filter((camel) => camel in data)
    .map((camel) => ({ dbKey: CAMEL_TO_SNAKE[camel], value: data[camel] }));
  if (updates.length === 0) return getSummaryById(id, userId);

  const setClause = updates.map((u, i) => `${u.dbKey} = $${i + 3}`).join(', ');
  const values = updates.map((u) => {
    const v = u.value;
    if (Array.isArray(v) || (typeof v === 'object' && v !== null)) return JSON.stringify(v);
    return v;
  });
  const result = await pool.query(
    `UPDATE summaries SET updated_at = now(), ${setClause} WHERE id = $1 AND user_id = $2 RETURNING *`,
    [id, userId, ...values]
  );
  return rowToSummary(result.rows[0]);
}
