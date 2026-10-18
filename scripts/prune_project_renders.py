"""Keep two finished pictures per project and delete the older render folders."""
import json
import sys

from backend.db import connect
from backend.render_retention import prune_pictures


def main():
    with connect() as db:
        busy = db.execute(
            "SELECT project_id, kind FROM jobs WHERE status IN ('queued','running')"
        ).fetchall()
        if busy:
            print('job_already_running', [dict(row) for row in busy])
            return 1
        rows = db.execute('SELECT id, result FROM projects').fetchall()
    freed = 0
    removed = 0
    for row in rows:
        result = json.loads(row['result'] or '{}')
        report = prune_pictures(row['id'], result.get('render_id') or '')
        if report['removed'] or report['audio']:
            print(row['id'], 'kept', report['kept'], 'removed', len(report['removed']), 'audio', len(report['audio']), 'freed', report['freed'])
            freed += report['freed']
            removed += len(report['removed'])
    print(f'removed_dirs={removed} freed_bytes={freed}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
