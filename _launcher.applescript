-- imgsearch 常驻启动器
-- on run  : 后台调用 launch.sh（秒返回，applet 不卡死）
-- on idle : 保持常驻 → dock 有图标、可右键退出
-- on quit : 退出时结束后台 python，释放模型内存与端口 57860
-- on reopen: 再次点击 dock 图标 → 打开网页

-- 不写 on run：命令行 osacompile 的 applet 在有 on run 时会执行完即退出，
-- 无法常驻。改为首次 on idle 里做初始化（started 只跑一次），之后靠 idle 常驻。
property started : false

on idle
	if not started then
		set started to true
		do shell script "/bin/bash \"/Users/cc/程序/imgsearch/launch.sh\" >>\"$HOME/.imgsearch/app.log\" 2>&1 &"
	end if
	return 3600
end idle

on reopen
	set p to "57860"
	try
		set p to do shell script "/usr/bin/python3 -c \"import json,os;print(int(json.load(open(os.path.expanduser('~/.imgsearch/config.json'))).get('port',57860)))\""
	end try
	do shell script "/usr/bin/open http://127.0.0.1:" & p
end reopen

on quit
	try
		do shell script "/usr/bin/pkill -f '.venv/bin/python gui.py'"
	end try
	continue quit
end quit
