kakaotalk-analyzer
==================

Litte Python script to get statistics from KakaoTalk message export files.

This is totally work-in-progress, but I will try to only put at
least kind of functional versions up on GitHub.

How to export messages
----------------------

- In the app, go to a chatroom and select Settings (설정) -> Export Messages (대화내용 이메일로 보내기) -> Send Text Messages Only (텍스트 메시지만 보내기)
- Send the export to your own email account

Usage
-----

Open a console and run `python kakaotalk.py path-to-file.txt action [period]`

Example output
--------------
![Example plot](http://f.cl.ly/items/3f0t1c3K1Y2n450u0z40/plot-output.png)