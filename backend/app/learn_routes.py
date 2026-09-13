from flask import Blueprint, jsonify, request
from .learn_data import LearnDB
import json

learn_bp = Blueprint('learn', __name__, url_prefix='/api/learn')


def _db():
    return LearnDB()


@learn_bp.route('/courses')
def list_courses():
    db = _db()
    category = request.args.get('category')
    rows = db.get_courses()
    result = []
    for r in rows:
        lessons = db.get_lessons(r[0])
        result.append({
            'id': r[0], 'title': r[1], 'description': r[2],
            'cover': r[3], 'category': r[4], 'video_url': r[5],
            'xp_reward': r[6], 'lesson_count': len(lessons)
        })
    if category:
        result = [c for c in result if c['category'] == category]
    return jsonify(result)


@learn_bp.route('/courses/<int:cid>')
def course_detail(cid):
    db = _db()
    r = db.get_course(cid)
    if not r:
        return jsonify({'error': 'not found'}), 404
    lessons = db.get_lessons(cid)
    return jsonify({
        'id': r[0], 'title': r[1], 'description': r[2],
        'cover': r[3], 'category': r[4], 'video_url': r[5], 'xp_reward': r[6],
        'lessons': [{'id': l[0], 'title': l[2], 'video_url': l[3], 'duration': l[4], 'order': l[5]} for l in lessons]
    })


@learn_bp.route('/lessons/<int:lid>/quizzes')
def lesson_quizzes(lid):
    db = _db()
    rows = db.get_quizzes(lid)
    return jsonify([{
        'id': r[0], 'question': r[2],
        'options': json.loads(r[3]) if isinstance(r[3], str) else r[3],
        'correct': r[4], 'order': r[5]
    } for r in rows])


@learn_bp.route('/lesson/<int:lid>/complete', methods=['POST'])
def complete_lesson(lid):
    db = _db()
    data = request.get_json() or {}
    user_id = data.get('user_id', 'anonymous')
    lesson = db.get_lesson(lid)
    if not lesson:
        return jsonify({'error': 'not found'}), 404
    course_id = lesson[1]
    db.complete_lesson(user_id, course_id, lid)
    xp_row = db.get_progress(user_id, course_id)
    xp = xp_row[3] if xp_row else 0

    achieved = []
    prog = db.get_progress(user_id)
    total_xp = sum(p[3] for p in prog) if prog else 0
    if total_xp >= 50:
        try: db.unlock_achievement(user_id, '初学者'); achieved.append('初学者')
        except: pass
    if total_xp >= 200:
        try: db.unlock_achievement(user_id, '学习达人'); achieved.append('学习达人')
        except: pass
    streak_row = db.get_progress(user_id, course_id)
    streak = streak_row[5] if streak_row else 0
    if streak >= 3:
        try: db.unlock_achievement(user_id, '连续打卡'); achieved.append('连续打卡')
        except: pass

    return jsonify({'xp': xp, 'xp_gained': 10, 'achievements': achieved})


@learn_bp.route('/progress')
def get_progress():
    db = _db()
    user_id = request.args.get('user_id', 'anonymous')
    prog = db.get_progress(user_id)
    if not prog:
        return jsonify({'xp': 0, 'points': 0, 'streak': 0, 'total_courses': 0})
    total_xp = sum(p[3] for p in prog)
    total_pts = sum(p[4] for p in prog)
    max_streak = max(p[5] for p in prog) if prog else 0
    return jsonify({'xp': total_xp, 'points': total_pts, 'streak': max_streak, 'total_courses': len(prog)})


@learn_bp.route('/achievements')
def get_achievements():
    db = _db()
    user_id = request.args.get('user_id', 'anonymous')
    return jsonify([{'name': r[0], 'unlocked_at': r[1]} for r in db.get_achievements(user_id)])