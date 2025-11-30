"""
前端界面模块
提供可视化的游戏管理界面
"""
from flask import Flask, render_template_string, jsonify
import os
import requests
import threading
import time
from datetime import datetime

# 前端服务器（用于展示界面）
frontend_app = Flask(__name__)

# 后端API地址
BACKEND_URL = "http://127.0.0.1:5000"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "host-secret")
ADMIN_HEADERS = {'X-Admin-Token': ADMIN_TOKEN}


def get_backend_data(endpoint, use_admin=False):
    """从后端获取数据"""
    try:
        headers = ADMIN_HEADERS if use_admin else None
        response = requests.get(f"{BACKEND_URL}{endpoint}", headers=headers, timeout=2)
        return response.json()
    except:
        return None


def post_backend_data(endpoint, data):
    """向后端发送POST请求"""
    try:
        response = requests.post(f"{BACKEND_URL}{endpoint}", json=data, timeout=2)
        return response.json()
    except:
        return None


# HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>谁是卧底 - 主持方平台</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        .section h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.5em;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: bold;
        }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            background: #667eea;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-right: 10px;
            margin-top: 10px;
        }
        button:hover {
            background: #5568d3;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .status {
            padding: 15px;
            background: #e3f2fd;
            border-radius: 5px;
            margin-bottom: 15px;
        }
        .status-item {
            margin: 5px 0;
            color: #333;
        }
        .groups-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .group-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            border: 2px solid #ddd;
        }
        .group-card.undercover {
            border-color: #f44336;
            background: #ffebee;
        }
        .group-card.civilian {
            border-color: #4caf50;
            background: #e8f5e9;
        }
        .group-card.eliminated {
            opacity: 0.5;
            text-decoration: line-through;
        }
        .descriptions {
            margin-top: 15px;
        }
        .description-item {
            background: white;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }
        .description-item .group-name {
            font-weight: bold;
            color: #667eea;
        }
        .description-item .time {
            color: #999;
            font-size: 0.9em;
        }
        .description-item.undercover {
            border-left-color: #f44336;
            background: #fff3e0;
        }
        .description-item.undercover .group-name {
            color: #f44336;
        }
        .round-divider {
            background: linear-gradient(90deg, #4CAF50, #2196F3);
            color: white;
            padding: 10px 15px;
            margin: 15px 0 10px 0;
            border-radius: 8px;
            font-weight: bold;
            text-align: center;
        }
        .countdown {
            font-size: 1.2em;
            color: #f44336;
            font-weight: bold;
        }
        .current-speaker {
            background: #fff3e0;
            border: 2px solid #ff9800;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }
        .speaker-panel {
            background: linear-gradient(135deg, #ff9800 0%, #f44336 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-top: 15px;
            text-align: center;
        }
        .speaker-name {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        .speaker-countdown {
            font-size: 3em;
            font-weight: bold;
            margin: 10px 0;
        }
        .speaker-countdown.warning {
            animation: blink 0.5s infinite;
        }
        @keyframes blink {
            50% { opacity: 0.5; }
        }
        .speaking-order {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
            justify-content: center;
        }
        .speaker-badge {
            padding: 8px 15px;
            border-radius: 20px;
            font-weight: bold;
        }
        .speaker-badge.done {
            background: #4caf50;
            color: white;
        }
        .speaker-badge.current {
            background: #ff9800;
            color: white;
            animation: pulse 1s infinite;
        }
        .speaker-badge.waiting {
            background: #e0e0e0;
            color: #666;
        }
        .speaker-badge.eliminated {
            background: #f44336;
            color: white;
            text-decoration: line-through;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        .reports {
            margin-top: 15px;
        }
        .report-item {
            background: white;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #ff9800;
        }
        .report-item .ticket {
            font-weight: bold;
            color: #ff9800;
        }
        .report-item .time {
            color: #999;
            font-size: 0.9em;
        }
        .vote-result {
            margin-top: 15px;
            padding: 15px;
            background: white;
            border-radius: 5px;
        }
        .vote-item {
            margin: 5px 0;
            padding: 5px;
            background: #f5f5f5;
        }
        .scores {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        .score-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border: 2px solid #667eea;
        }
        .score-value {
            font-size: 2em;
            color: #667eea;
            font-weight: bold;
        }
        .message {
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .message.success {
            background: #d4edda;
            color: #155724;
        }
        .message.error {
            background: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 谁是卧底 - 主持方平台</h1>
        
        <!-- 游戏控制区域 -->
        <div class="section">
            <h2>游戏控制</h2>
            <div class="form-group">
                <label>卧底词：</label>
                <input type="text" id="undercover-word" placeholder="输入卧底词">
            </div>
            <div class="form-group">
                <label>平民词：</label>
                <input type="text" id="civilian-word" placeholder="输入平民词">
            </div>
            <button onclick="startGame()">开始游戏</button>
            <button onclick="startRound()">开始新回合</button>
            <button onclick="processVoting()">处理投票结果</button>
            <button onclick="resetGame()">重置游戏</button>
        </div>
        
        <!-- 游戏状态 -->
        <div class="section">
            <h2>游戏状态</h2>
            <div class="status" id="game-status">
                <div class="status-item">状态：等待注册</div>
                <div class="status-item">当前回合：0</div>
                <div class="status-item">已注册组数：0</div>
            </div>
            <!-- 发言者面板 -->
            <div id="speaker-panel" style="display: none;">
                <div class="speaker-panel">
                    <div>🎤 当前发言</div>
                    <div class="speaker-name" id="current-speaker-name">---</div>
                    <div>剩余时间</div>
                    <div class="speaker-countdown" id="speaker-countdown">--</div>
                </div>
                <div class="speaking-order" id="speaking-order"></div>
            </div>
        </div>
        
        <!-- 注册的组 -->
        <div class="section">
            <h2>已注册的组</h2>
            <div class="groups-list" id="groups-list"></div>
        </div>
        
        <!-- 描述展示 -->
        <div class="section">
            <h2>当前回合描述</h2>
            <div class="descriptions" id="descriptions"></div>
        </div>
        
        <!-- 投票结果 -->
        <div class="section">
            <h2>投票结果</h2>
            <div class="vote-result" id="vote-result"></div>
        </div>

        <!-- 异常上报 -->
        <div class="section">
            <h2>异常上报</h2>
            <div class="reports" id="reports"></div>
        </div>
        
        <!-- 得分 -->
        <div class="section">
            <h2>得分</h2>
            <div class="scores" id="scores"></div>
        </div>
    </div>
    
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <script>
        // WebSocket 连接
        const socket = io('http://127.0.0.1:5000');
        
        // 连接成功
        socket.on('connect', function() {
            console.log('WebSocket 已连接');
        });
        
        // 接收状态更新推送
        socket.on('status_update', function(data) {
            console.log('收到状态推送:', data);
            updateSpeakerPanel(data);
        });
        
        // 接收完整游戏状态推送
        socket.on('game_state_update', function(data) {
            console.log('收到游戏状态推送:', data);
            updateStatus(data);
            updateGroups(data);
            updateDescriptions(data);
            updateReports(data);
            updateScores(data);
        });
        
        // 接收投票结果推送
        socket.on('vote_result', function(data) {
            console.log('收到投票结果推送:', data);
            updateVoteResult(data);
        });
        
        // 断开连接时的处理
        socket.on('disconnect', function() {
            console.log('WebSocket 已断开，将使用轮询');
        });
        
        // 本地倒计时变量
        let localSpeakerRemaining = null;
        let localPhaseRemaining = null;
        let currentStatus = null;
        
        // 本地倒计时（每秒更新）
        setInterval(function() {
            if (localSpeakerRemaining !== null && localSpeakerRemaining > 0) {
                localSpeakerRemaining--;
                updateCountdownDisplay();
            }
            if (localPhaseRemaining !== null && localPhaseRemaining > 0) {
                localPhaseRemaining--;
            }
        }, 1000);
        
        function updateCountdownDisplay() {
            const countdown = document.getElementById('speaker-countdown');
            if (countdown && localSpeakerRemaining !== null) {
                countdown.textContent = localSpeakerRemaining + ' 秒';
                if (localSpeakerRemaining <= 10) {
                    countdown.classList.add('warning');
                } else {
                    countdown.classList.remove('warning');
                }
            }
        }
        
        // 备用轮询（WebSocket 断开时使用）
        setInterval(function() {
            if (!socket.connected) {
                updateGameState();
                updateSpeakerStatusFallback();
            }
        }, 2000);
        
        // 初始加载
        updateGameState();
        
        function updateSpeakerStatusFallback() {
            fetch('/api/public/status')
                .then(response => response.json())
                .then(resp => {
                    if (resp && resp.code === 200) {
                        updateSpeakerPanel(resp.data || {});
                    }
                })
                .catch(error => console.error('Error:', error));
        }
        
        function updateSpeakerPanel(data) {
            const panel = document.getElementById('speaker-panel');
            const speakerName = document.getElementById('current-speaker-name');
            const countdown = document.getElementById('speaker-countdown');
            const orderDiv = document.getElementById('speaking-order');
            
            // 保存当前状态
            currentStatus = data.status;
            
            if (data.status === 'describing') {
                panel.style.display = 'block';
                
                // 当前发言者
                const current = data.current_speaker || '---';
                speakerName.textContent = current;
                
                // 更新本地倒计时（从服务器同步）
                if (data.speaker_remaining_seconds !== null && data.speaker_remaining_seconds !== undefined) {
                    localSpeakerRemaining = data.speaker_remaining_seconds;
                }
                if (data.remaining_seconds !== null && data.remaining_seconds !== undefined) {
                    localPhaseRemaining = data.remaining_seconds;
                }
                
                // 显示倒计时
                updateCountdownDisplay();
                
                // 发言顺序
                const order = data.describe_order || [];
                const currentIdx = data.current_speaker_index || 0;
                const eliminated = data.eliminated_groups || [];
                
                let orderHtml = '';
                for (let i = 0; i < order.length; i++) {
                    const name = order[i];
                    let badgeClass = 'waiting';
                    let icon = '⬜';
                    
                    if (eliminated.includes(name)) {
                        badgeClass = 'eliminated';
                        icon = '❌';
                    } else if (i < currentIdx) {
                        badgeClass = 'done';
                        icon = '✅';
                    } else if (i === currentIdx) {
                        badgeClass = 'current';
                        icon = '🎤';
                    }
                    
                    orderHtml += `<div class="speaker-badge ${badgeClass}">${icon} ${name}</div>`;
                }
                orderDiv.innerHTML = orderHtml;
                
            } else if (data.status === 'voting') {
                panel.style.display = 'block';
                
                // 显示投票进度
                const votedGroups = data.voted_groups || [];
                const activeGroups = data.active_groups || [];
                speakerName.textContent = `🗳️ 投票中 (${votedGroups.length}/${activeGroups.length})`;
                
                // 更新本地倒计时
                if (data.remaining_seconds !== null && data.remaining_seconds !== undefined) {
                    localSpeakerRemaining = data.remaining_seconds;
                    localPhaseRemaining = data.remaining_seconds;
                }
                updateCountdownDisplay();
                
                // 显示投票状态：谁已投票，谁未投票
                const order = data.describe_order || [];
                const eliminated = data.eliminated_groups || [];
                let orderHtml = '';
                for (const name of order) {
                    if (eliminated.includes(name)) {
                        orderHtml += `<div class="speaker-badge eliminated">❌ ${name}</div>`;
                    } else if (votedGroups.includes(name)) {
                        orderHtml += `<div class="speaker-badge done">✅ ${name}</div>`;
                    } else {
                        orderHtml += `<div class="speaker-badge waiting">⏳ ${name}</div>`;
                    }
                }
                orderDiv.innerHTML = orderHtml;
                
            } else if (data.status === 'round_end' || data.status === 'game_end') {
                // 回合结束或游戏结束，停止倒计时并隐藏面板
                panel.style.display = 'none';
                localSpeakerRemaining = null;
                localPhaseRemaining = null;
            } else {
                panel.style.display = 'none';
                localSpeakerRemaining = null;
                localPhaseRemaining = null;
            }
        }
        
        function updateGameState() {
            fetch('/api/game/state')
                .then(response => response.json())
                .then(resp => {
                    if (resp && resp.code === 200) {
                        const data = resp.data || {};
                        updateStatus(data);
                        updateGroups(data);
                        updateDescriptions(data);
                        updateReports(data);
                        updateScores(data);
                    } else {
                        console.error('状态刷新失败：', resp ? resp.message : '未知错误');
                    }
                })
                .catch(error => console.error('Error:', error));
        }
        
        function updateStatus(data) {
            const statusDiv = document.getElementById('game-status');
            const statusMap = {
                'waiting': '等待注册',
                'registered': '已注册',
                'word_assigned': '词语已分配',
                'describing': '描述阶段',
                'voting': '投票阶段',
                'round_end': '回合结束',
                'game_end': '游戏结束'
            };
            
            // 获取发言顺序和当前发言人
            let speakerInfo = '';
            if (data.describe_order && data.describe_order.length > 0) {
                speakerInfo = `<div class="status-item">发言顺序：${data.describe_order.join(' → ')}</div>`;
            }
            
            // 当前发言者
            let currentSpeakerInfo = '';
            if (data.status === 'describing' && data.current_speaker) {
                currentSpeakerInfo = `<div class="status-item" style="color: #ff9800; font-weight: bold;">🎤 当前发言：${data.current_speaker}</div>`;
            }
            
            // 已发言的组
            let describedInfo = '';
            if (data.described_groups && data.described_groups.length > 0) {
                describedInfo = `<div class="status-item" style="color: #4caf50;">✅ 已发言：${data.described_groups.join(', ')}</div>`;
            }
            
            // 已投票的组
            let votedInfo = '';
            if (data.status === 'voting' && data.voted_groups && data.voted_groups.length > 0) {
                const activeCount = data.describe_order ? data.describe_order.filter(g => !data.eliminated_groups?.includes(g)).length : 0;
                votedInfo = `<div class="status-item" style="color: #2196f3;">🗳️ 已投票：${data.voted_groups.join(', ')} (${data.voted_groups.length}/${activeCount})</div>`;
            }
            
            statusDiv.innerHTML = `
                <div class="status-item">状态：${statusMap[data.status] || data.status}</div>
                <div class="status-item">当前回合：${data.current_round || 0}</div>
                <div class="status-item">已注册组数：${Object.keys(data.groups || {}).length}</div>
                ${data.undercover_group ? `<div class="status-item">卧底组：${data.undercover_group}</div>` : ''}
                ${speakerInfo}
                ${currentSpeakerInfo}
                ${describedInfo}
                ${votedInfo}
            `;
        }
        
        function updateGroups(data) {
            const groupsList = document.getElementById('groups-list');
            if (!data.groups) {
                groupsList.innerHTML = '<p>暂无注册的组</p>';
                return;
            }
            
            let html = '';
            for (const [name, info] of Object.entries(data.groups)) {
                const role = info.role || 'unknown';
                const eliminated = info.eliminated || false;
                html += `
                    <div class="group-card ${role} ${eliminated ? 'eliminated' : ''}">
                        <div><strong>${name}</strong></div>
                        <div>${role === 'undercover' ? '卧底' : role === 'civilian' ? '平民' : '未知'}</div>
                        ${eliminated ? '<div style="color: red;">已淘汰</div>' : ''}
                    </div>
                `;
            }
            groupsList.innerHTML = html;
        }
        
        function updateDescriptions(data) {
            const descDiv = document.getElementById('descriptions');
            const allDescriptions = data.descriptions || {};
            const rounds = Object.keys(allDescriptions);
            if (rounds.length === 0) {
                descDiv.innerHTML = '<p>暂无描述</p>';
                return;
            }

            // 按回合顺序排列（从新到旧）
            const numericRounds = rounds.map(r => parseInt(r, 10)).sort((a, b) => b - a);
            
            let html = '';
            let hasAnyDescription = false;
            
            // 显示所有回合的描述
            for (const roundNum of numericRounds) {
                const roundDescriptions = allDescriptions[roundNum] || [];
                if (roundDescriptions.length > 0) {
                    hasAnyDescription = true;
                    
                    // 回合分界线
                    html += `<div class="round-divider">📢 第 ${roundNum} 回合 (${roundDescriptions.length}人发言)</div>`;
                    
                    for (const desc of roundDescriptions) {
                        const time = new Date(desc.time).toLocaleTimeString('zh-CN');
                        const isUndercover = data.undercover_group && desc.group === data.undercover_group;
                        html += `
                            <div class="description-item ${isUndercover ? 'undercover' : ''}">
                                <div class="group-name">${desc.group} ${isUndercover ? '👤(卧底)' : ''}</div>
                                <div>${desc.description}</div>
                                <div class="time">${time}</div>
                            </div>
                        `;
                    }
                }
            }
            
            if (!hasAnyDescription) {
                html = '<p>暂无描述</p>';
            }
            
            descDiv.innerHTML = html;
        }

        function updateReports(data) {
            const reportsDiv = document.getElementById('reports');
            const reports = data.reports || [];
            if (reports.length === 0) {
                reportsDiv.innerHTML = '<p>暂无异常上报</p>';
                return;
            }

            const latestReports = reports.slice(-10).reverse();
            let html = '';
            for (const report of latestReports) {
                const time = new Date(report.time).toLocaleTimeString('zh-CN');
                html += `
                    <div class="report-item">
                        <div class="ticket">${report.ticket}</div>
                        <div>组：${report.group}</div>
                        <div>类型：${report.type}</div>
                        <div>${report.detail}</div>
                        <div class="time">${time}</div>
                    </div>
                `;
            }
            reportsDiv.innerHTML = html;
        }
        
        function updateScores(data) {
            const scoresDiv = document.getElementById('scores');
            if (!data.scores || Object.keys(data.scores).length === 0) {
                scoresDiv.innerHTML = '<p>暂无得分</p>';
                return;
            }
            
            let html = '';
            for (const [group, score] of Object.entries(data.scores)) {
                html += `
                    <div class="score-card">
                        <div>${group}</div>
                        <div class="score-value">${score}</div>
                    </div>
                `;
            }
            scoresDiv.innerHTML = html;
        }
        
        function updateVoteResult(data) {
            const voteDiv = document.getElementById('vote-result');
            let html = '';
            
            // 显示提示信息
            if (data.message) {
                html += `<div class="vote-item" style="font-size: 1.2em; padding: 10px; background: #e3f2fd; border-radius: 5px; margin-bottom: 10px;">${data.message}</div>`;
            }
            
            // 得票统计
            html += '<div class="vote-item"><strong>📊 得票统计：</strong></div>';
            for (const [group, votes] of Object.entries(data.vote_count || {})) {
                html += `<div class="vote-item">${group}: ${votes}票</div>`;
            }
            
            // 淘汰信息
            if (data.eliminated && data.eliminated.length > 0) {
                html += `<div class="vote-item" style="color: red; font-weight: bold;">💀 淘汰：${data.eliminated.join(', ')}</div>`;
            }
            
            // 游戏结束信息
            if (data.game_ended) {
                const winnerText = data.winner === 'undercover' ? '🎭 卧底胜利！' : '👥 平民胜利！';
                html += `<div class="vote-item" style="font-size: 1.5em; color: ${data.winner === 'undercover' ? '#f44336' : '#4caf50'}; font-weight: bold; margin-top: 10px;">${winnerText}</div>`;
                
                // 揭示卧底身份和词语
                if (data.undercover_group) {
                    html += `<div class="vote-item" style="background: #fff3e0; padding: 10px; border-radius: 5px; margin-top: 10px;">`;
                    html += `<div style="font-weight: bold;">🎭 卧底是：${data.undercover_group}</div>`;
                    html += `<div>卧底词：<strong>${data.undercover_word || '???'}</strong></div>`;
                    html += `<div>平民词：<strong>${data.civilian_word || '???'}</strong></div>`;
                    html += `</div>`;
                }
                
                // 显示最终得分
                if (data.final_scores && Object.keys(data.final_scores).length > 0) {
                    html += `<div class="vote-item" style="margin-top: 10px;"><strong>🏆 最终得分：</strong></div>`;
                    // 按分数排序
                    const sortedScores = Object.entries(data.final_scores).sort((a, b) => b[1] - a[1]);
                    for (const [group, score] of sortedScores) {
                        const isUndercover = group === data.undercover_group;
                        const medal = sortedScores.indexOf(sortedScores.find(s => s[0] === group)) === 0 ? '🥇' : 
                                      sortedScores.indexOf(sortedScores.find(s => s[0] === group)) === 1 ? '🥈' : 
                                      sortedScores.indexOf(sortedScores.find(s => s[0] === group)) === 2 ? '🥉' : '';
                        html += `<div class="vote-item" style="color: ${isUndercover ? '#f44336' : '#333'};">${medal} ${group}${isUndercover ? '(卧底)' : ''}: ${score}分</div>`;
                    }
                }
            }
            
            voteDiv.innerHTML = html;
        }
        
        function startGame() {
            const undercoverWord = document.getElementById('undercover-word').value;
            const civilianWord = document.getElementById('civilian-word').value;
            
            if (!undercoverWord || !civilianWord) {
                alert('请输入卧底词和平民词');
                return;
            }
            
            fetch('/api/game/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    undercover_word: undercoverWord,
                    civilian_word: civilianWord
                })
            })
            .then(response => response.json())
            .then(resp => {
                if (resp && resp.code === 200) {
                    alert(resp.message || '游戏已开始！');
                    updateGameState();
                } else {
                    alert('错误：' + (resp ? resp.message : '后端无响应'));
                }
            })
            .catch(error => {
                alert('请求失败：' + error);
            });
        }
        
        function startRound() {
            fetch('/api/game/round/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(response => response.json())
            .then(resp => {
                if (resp && resp.code === 200) {
                    const payload = resp.data || {};
                    const orderText = payload.order ? ` 顺序：${payload.order.join(' -> ')}` : '';
                    alert((resp.message || '回合已开始！') + orderText);
                    updateGameState();
                } else {
                    alert('错误：' + (resp ? resp.message : '后端无响应'));
                }
            })
            .catch(error => {
                alert('请求失败：' + error);
            });
        }
        
        function processVoting() {
            fetch('/api/game/voting/process', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(response => response.json())
            .then(resp => {
                if (resp && resp.code === 200) {
                    const data = resp.data || {};
                    
                    // 使用服务器返回的提示信息
                    let message = data.message || '投票结果已处理';
                    
                    if (data.game_ended) {
                        message += '\\n\\n🎭 卧底是：' + data.undercover_group;
                        message += '\\n卧底词：' + data.undercover_word;
                        message += '\\n平民词：' + data.civilian_word;
                        
                        if (data.final_scores) {
                            message += '\\n\\n🏆 最终得分：';
                            for (const [group, score] of Object.entries(data.final_scores)) {
                                message += `\\n${group}: ${score}分`;
                            }
                        }
                    }
                    alert(message);
                    
                    // 更新投票结果显示
                    const voteDiv = document.getElementById('vote-result');
                    let html = '<div class="vote-item">得票统计：</div>';
                    for (const [group, votes] of Object.entries(data.vote_count || {})) {
                        html += `<div class="vote-item">${group}: ${votes}票</div>`;
                    }
                    if (data.eliminated && data.eliminated.length > 0) {
                        html += `<div class="vote-item" style="color: red;">淘汰：${data.eliminated.join(', ')}</div>`;
                    }
                    voteDiv.innerHTML = html;
                    
                    updateGameState();
                } else {
                    alert('错误：' + (resp ? resp.message : '后端无响应'));
                }
            })
            .catch(error => {
                alert('请求失败：' + error);
            });
        }
        
        function resetGame() {
            if (confirm('确定要重置游戏吗？')) {
                fetch('/api/game/reset', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                })
                .then(response => response.json())
                .then(resp => {
                    if (resp && resp.code === 200) {
                        alert(resp.message || '游戏已重置');
                        updateGameState();
                        document.getElementById('vote-result').innerHTML = '';
                    } else {
                        alert('错误：' + (resp ? resp.message : '后端无响应'));
                    }
                })
                .catch(error => {
                    alert('请求失败：' + error);
                });
            }
        }
    </script>
</body>
</html>
"""


@frontend_app.route('/')
def index():
    """主页面"""
    return render_template_string(HTML_TEMPLATE)


@frontend_app.route('/api/game/state')
def api_game_state():
    """代理后端API"""
    data = get_backend_data('/api/game/state', use_admin=True)
    if data is None:
        return jsonify({"code": 500, "message": "后端状态接口无响应", "data": {}}), 500
    return jsonify(data)


@frontend_app.route('/api/public/status')
def api_public_status():
    """代理后端公开状态API（获取发言者和倒计时）"""
    data = get_backend_data('/api/status', use_admin=False)
    if data is None:
        return jsonify({"code": 500, "message": "后端状态接口无响应", "data": {}}), 500
    return jsonify(data)


@frontend_app.route('/api/game/start', methods=['POST'])
def api_start_game():
    """代理后端API"""
    from flask import request
    data = request.json
    response = requests.post(
        f"{BACKEND_URL}/api/game/start",
        json=data,
        headers=ADMIN_HEADERS,
        timeout=2
    )
    return jsonify(response.json()), response.status_code


@frontend_app.route('/api/game/round/start', methods=['POST'])
def api_start_round():
    """代理后端API"""
    response = requests.post(
        f"{BACKEND_URL}/api/game/round/start",
        headers=ADMIN_HEADERS,
        timeout=2
    )
    return jsonify(response.json()), response.status_code


@frontend_app.route('/api/game/voting/process', methods=['POST'])
def api_process_voting():
    """代理后端API"""
    response = requests.post(
        f"{BACKEND_URL}/api/game/voting/process",
        headers=ADMIN_HEADERS,
        timeout=2
    )
    return jsonify(response.json()), response.status_code


@frontend_app.route('/api/game/reset', methods=['POST'])
def api_reset_game():
    """代理后端API"""
    response = requests.post(
        f"{BACKEND_URL}/api/game/reset",
        headers=ADMIN_HEADERS,
        timeout=2
    )
    return jsonify(response.json()), response.status_code


if __name__ == '__main__':
    print("=" * 50)
    print("前端界面服务器启动中...")
    print("访问地址: http://127.0.0.1:5001")
    print("=" * 50)
    print("注意：请确保后端服务器(backend.py)已启动")
    print("=" * 50)
    
    # 前端服务器运行在5001端口
    frontend_app.run(host='0.0.0.0', port=5001, debug=True)

