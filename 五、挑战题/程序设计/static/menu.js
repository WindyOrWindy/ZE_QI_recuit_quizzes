 //menu.js —— 左侧菜单切换（四个页面共用)
document.addEventListener('DOMContentLoaded', function () {

    // 路由与菜单 id 的对应关系
    var PATH_MAP = {
        '/register':  'sign_up',
        '/login':     'sign_in',
        '/user_list': 'users_list',
        '/me':        'self'
    };

    //个人中心子项 id 与 action 参数的对应关系 
    var SUB_ACTION = {
        'self_info':           'info',
        'self_edit_username':  'username',
        'self_edit_password':  'password',
        'self_delete':         'delete'
    };

    //当前页面状态 
    var path   = location.pathname.replace(/\/+$/, '') || '/';
    var action = new URLSearchParams(location.search).get('action') || 'info';

     // 高亮：清除后按当前 URL 重新标记
    function markActive() {
        var items = document.querySelectorAll('.left_item');
        for (var i = 0; i < items.length; i++) {
            items[i].classList.remove('active');
        }

        // 一级菜单
        var topId = PATH_MAP[path];
        var topEl = topId && document.getElementById(topId);
        if (topEl) topEl.classList.add('active');

        // /me 页面额外高亮子项
        if (path === '/me') {
            for (var subId in SUB_ACTION) {
                if (SUB_ACTION[subId] === action) {
                    var subEl = document.getElementById(subId);
                    if (subEl) subEl.classList.add('active');
                }
            }
        }
    }


     // 面板切换

    function showPanel(name) {
        var panels = document.querySelectorAll('[data-panel]');
        for (var i = 0; i < panels.length; i++) {
            var p = panels[i];
            p.style.display = (p.getAttribute('data-panel') === name) ? 'block' : 'none';
        }
        // 同步每个面板里的请求方式说明
        var hint = document.getElementById('action_hint');
        if (hint) hint.textContent = PANEL_API[name] || '';
    }

    //接口说明（显示在面板顶部）
    var PANEL_API = {
        'info':     'GET /users/me',
        'username': 'PATCH /users/me  { new_username, password }',
        'password': 'PATCH /users/me  { old_password, new_password }',
        'delete':   'DELETE /users/me  { password }'
    };

   
    // 跳转
    function bindTopNav(id, href) {
        var el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (path !== href) location.href = href;   // 当前页就点了不动
        });
    }
    bindTopNav('sign_up',    '/register');
    bindTopNav('sign_in',    '/login');
    bindTopNav('users_list', '/user_list');

    // 个人中心
    function switchAction(name) {
        if (path === '/me') {
            // 已经在 /me：本地切面板，不重新加载页面
            action = name;
            history.pushState({ action: name }, '', '/me?action=' + name);
            showPanel(name);
            markActive();
        } else {
            // 不在 /me：整页跳过去
            location.href = '/me?action=' + name;
        }
    }

    // 父项「个人中心」：点到标题才跳，点到子项交给子项处理
    var selfEl = document.getElementById('self');
    if (selfEl) {
        selfEl.addEventListener('click', function (e) {
            if (e.target !== this) return;   // 点在子区域，不拦截
            e.preventDefault();
            switchAction('info');
        });
    }

    // 4 个子项
    Object.keys(SUB_ACTION).forEach(function (subId) {
        var el = document.getElementById(subId);
        if (!el) return;
        el.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();             // 阻止冒泡到「个人中心」
            switchAction(SUB_ACTION[subId]);
        });
    });


    // 浏览器前进 / 后退

    window.addEventListener('popstate', function () {
        action = new URLSearchParams(location.search).get('action') || 'info';
        showPanel(action);
        markActive();
    });


     // 初始化
    markActive();
    if (path === '/me') showPanel(action);

});
