"""The delivery selection is separate from the immutable render Master."""
import time


def init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS project_final_outputs(
        project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
        master_id TEXT NOT NULL, version_id TEXT NOT NULL, updated REAL NOT NULL)''')

    from .final_music import init as init_music
    init_music(db)


def select(db, pid, master_id, version_id):
    db.execute('''INSERT INTO project_final_outputs(project_id,master_id,version_id,updated)
        VALUES(?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET
        master_id=excluded.master_id,version_id=excluded.version_id,updated=excluded.updated''',
        (pid, master_id, version_id, time.time()))


def current(db, pid, master_id):
    """A newer render must never inherit a voiceover of an older edit."""
    row = db.execute('''SELECT v.* FROM project_final_outputs f
        JOIN dubbing_versions v ON v.id=f.version_id AND v.project_id=f.project_id
        WHERE f.project_id=? AND f.master_id=? AND v.master_id=f.master_id
        AND v.kind='video' AND v.status='ready' ''', (pid, master_id)).fetchone()

    if row:return dict(row)|{'delivery':'dub'}
    row=db.execute("""SELECT m.*,v.language,v.voice FROM project_final_outputs f
      JOIN final_music_versions m ON m.id=f.version_id AND m.project_id=f.project_id
      LEFT JOIN dubbing_versions v ON v.id=m.source_voice AND v.project_id=m.project_id
      WHERE f.project_id=? AND f.master_id=? AND m.master_id=f.master_id AND m.status='ready'""",(pid,master_id)).fetchone()
    return dict(row)|{'delivery':'mix','kind':'mix','progress':100,'language':row['language'] or '', 'voice':row['voice'] or ''} if row else None


def path(pid,row):
    from .config import settings
    return settings.data_dir/pid/('audio-mixes' if row.get('delivery')=='mix' else 'dubbing')/row['id']/'video.mp4'
