"""
后端服务器模块
提供RESTful API接口，处理游戏方的请求
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from game_logic import GameLogic, GameStatus
import os
import threading
import socket

app = Flask(__name__)
CORS(app)  # 允许跨域请求
socketio = SocketIO(app, cors_allowed_origins="*")  # WebSocket支持

# 管理员令牌（主持方专用）
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "host-secret")

# 全局游戏逻辑实例
game = GameLogic()

# 线程锁，保证线程安全
game_lock = threading.Lock()


def broadcast_status():
    """广播游戏状态变化"""
    with game_lock:
        status = game.get_public_status()
    socketio.emit('status_update', status)


def broadcast_game_state():
    """广播完整游戏状态（主持方用）"""
    with game_lock:
        state = game.get_game_state()
    socketio.emit('game_state_update', state)


def get_local_ip():
    """获取本机局域网IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def _require_admin():
    """校验主持方权限"""
    header_token = request.headers.get("X-Admin-Token", "")
    return header_token == ADMIN_TOKEN


def _admin_forbidden_response():
    return make_response({}, 403, '无权限：需要主持方令牌')


def make_response(data=None, code=200, message="ok"):
    payload = {
        "code": code,
        "message": message,
        "data": data or {}
    }
    return jsonify(payload), code


@app.route('/api/register', methods=['POST'])
def register():
    """游戏方注册接口"""
    data = request.json
    group_name = data.get('group_name') or data.get('group_id', '')
    group_name = group_name.strip() if isinstance(group_name, str) else ''
    
    if not group_name:
        return make_response({}, 400, '组名不能为空')
    
    with game_lock:
        success = game.register_group(group_name)
        if success:
            # 广播状态变化
            socketio.start_background_task(broadcast_status)
            socketio.start_background_task(broadcast_game_state)
            return make_response({
                'group_name': group_name,
                'total_groups': len(game.groups)
            }, 200, '注册成功')
        else:
            return make_response({}, 400, '注册失败：组名已存在或已达到最大组数(5组)')


@app.route('/api/game/start', methods=['POST'])
def start_game():
    """开始游戏接口（主持方调用）"""
    if not _require_admin():
        return _admin_forbidden_response()
    data = request.json
    undercover_word = data.get('undercover_word', '').strip()
    civilian_word = data.get('civilian_word', '').strip()
    
    if not undercover_word or not civilian_word:
        return make_response({}, 400, '词语不能为空')
    
    with game_lock:
        success = game.start_game(undercover_word, civilian_word)
        if success:
            # 广播状态变化
            socketio.start_background_task(broadcast_status)
            socketio.start_background_task(broadcast_game_state)
            return make_response({
                'undercover_group': game.undercover_group,
                'groups': {name: info['role'] for name, info in game.groups.items()}
            }, 200, '游戏已开始')
        else:
            return make_response({}, 400, '无法开始游戏：游戏状态不正确或没有注册的组')


@app.route('/api/game/round/start', methods=['POST'])
def start_round():
    """开始新回合接口（主持方调用）"""
    if not _require_admin():
        return _admin_forbidden_response()
    with game_lock:
        order = game.start_round()
        if order:
            # 广播状态变化
            socketio.start_background_task(broadcast_status)
            socketio.start_background_task(broadcast_game_state)
            return make_response({
                'round': game.current_round,
                'order': order
            }, 200, '回合已开始')
        else:
            return make_response({}, 400, '无法开始回合：游戏状态不正确或活跃组数不足')


@app.route('/api/describe', methods=['POST'])
def submit_description():
    """提交描述接口（游戏方调用）"""
    data = request.json
    group_name = data.get('group_name', '').strip()
    description = data.get('description', '').strip()
    
    if not group_name or not description:
        return make_response({}, 400, '组名和描述不能为空')
    
    with game_lock:
        success, message = game.submit_description(group_name, description)
        if success:
            # 广播状态变化
            socketio.start_background_task(broadcast_status)
            socketio.start_background_task(broadcast_game_state)
            # 获取当前描述列表
            current_descriptions = game.descriptions.get(game.current_round, [])
            return make_response({
                'round': game.current_round,
                'total_descriptions': len(current_descriptions)
            }, 200, message)
        else:
            return make_response({
                'current_speaker': game.get_current_speaker()
            }, 200, message)  # 返回200但提示需要等待


@app.route('/api/vote', methods=['POST'])
def submit_vote():
    """提交投票接口（游戏方调用）"""
    data = request.json
    voter_group = data.get('voter_group', '').strip()
    target_group = data.get('target_group', '').strip()
    
    if not voter_group or not target_group:
        return make_response({}, 400, '投票者和被投票者不能为空')
    
    with game_lock:
        success = game.submit_vote(voter_group, target_group)
        if success:
            # 广播状态变化
            socketio.start_background_task(broadcast_status)
            return make_response({}, 200, '投票提交成功')
        else:
            return make_response({}, 400, '投票提交失败：游戏状态不正确、组名无效或不能投自己')


@app.route('/api/game/voting/process', methods=['POST'])
def process_voting():
    """处理投票结果接口（主持方调用）"""
    if not _require_admin():
        return _admin_forbidden_response()
    with game_lock:
        result = game.process_voting_result()
        if 'error' in result:
            return make_response(result, 400, result.get('error', '投票处理失败'))
        # 广播状态变化
        socketio.start_background_task(broadcast_status)
        socketio.start_background_task(broadcast_game_state)
        # 广播投票结果
        socketio.emit('vote_result', result)
        return make_response(result, 200, '投票结果已生成')


@app.route('/api/game/state', methods=['GET'])
def get_game_state():
    """获取游戏状态接口"""
    if not _require_admin():
        return _admin_forbidden_response()
    with game_lock:
        state = game.get_game_state()
        return make_response(state)


@app.route('/api/status', methods=['GET'])
def public_status():
    """游戏方公共状态接口"""
    with game_lock:
        status = game.get_public_status()
        return make_response(status)


@app.route('/api/result', methods=['GET'])
def public_result():
    """最近一次投票结果"""
    with game_lock:
        result = game.get_last_result()
        if not result:
            return make_response({}, 404, '当前暂无投票结果')
        return make_response(result)


@app.route('/api/word', methods=['GET'])
def get_word():
    """获取词语接口（游戏方调用，仅返回自己的词语）"""
    group_name = request.args.get('group_name', '').strip()
    
    if not group_name:
        return make_response({}, 400, '组名不能为空')
    
    with game_lock:
        word = game.get_group_word(group_name)
        if word:
            return make_response({'word': word})
        else:
            return make_response({}, 404, '未找到该组的词语或游戏未开始')


@app.route('/api/descriptions', methods=['GET'])
def get_descriptions():
    """获取当前回合的描述列表（游戏方调用）"""
    round_num = request.args.get('round', type=int)
    
    with game_lock:
        if round_num is None:
            round_num = game.current_round
        
        descriptions = game.descriptions.get(round_num, [])
        result = []
        for desc in descriptions:
            result.append({
                'group': desc['group'],
                'description': desc['description']
            })
        
        return make_response({
            'round': round_num,
            'descriptions': result,
            'total': len(result)
        })


@app.route('/api/game/reset', methods=['POST'])
def reset_game():
    """重置游戏接口（主持方调用）"""
    if not _require_admin():
        return _admin_forbidden_response()
    with game_lock:
        game.reset_game()
        # 广播状态变化
        socketio.start_background_task(broadcast_status)
        socketio.start_background_task(broadcast_game_state)
        return make_response({}, 200, '游戏已重置')


@app.route('/api/report', methods=['POST'])
def report_issue():
    """异常上报接口（游戏方调用）"""
    data = request.json or {}
    group_name = data.get('group_name') or data.get('group_id', '')
    group_name = group_name.strip() if isinstance(group_name, str) else ''
    report_type = data.get('type', 'general').strip() or 'general'
    detail = data.get('detail', '').strip()

    if not detail:
        return make_response({}, 400, 'detail不能为空')

    with game_lock:
        report_entry = game.add_report(group_name, report_type, detail)

    return make_response({
        'ticket': report_entry['ticket'],
        'recorded_at': report_entry['time']
    }, 200, '异常已记录')


@app.route('/api/groups', methods=['GET'])
def get_groups():
    """获取所有注册的组接口"""
    with game_lock:
        groups_info = []
        for name, info in game.groups.items():
            groups_info.append({
                'name': name,
                'registered_time': info['registered_time'],
                'eliminated': name in game.eliminated_groups
            })
        return make_response({
            'groups': groups_info,
            'total': len(groups_info)
        })


# WebSocket事件处理
@socketio.on('connect')
def handle_connect():
    """客户端连接时发送当前状态"""
    with game_lock:
        status = game.get_public_status()
    emit('status_update', status)


@socketio.on('request_status')
def handle_request_status():
    """客户端请求状态更新"""
    with game_lock:
        status = game.get_public_status()
    emit('status_update', status)


if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"=" * 50)
    print(f"谁是卧底 - 主持方平台")
    print(f"=" * 50)
    print(f"服务器启动中...")
    print(f"本地访问: http://127.0.0.1:5000")
    print(f"局域网访问: http://{local_ip}:5000")
    print(f"WebSocket: 已启用实时推送")
    print(f"=" * 50)
    print(f"请确保游戏方能够访问上述IP地址")
    print(f"=" * 50)
    
    # 使用 socketio.run 替代 app.run
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)

