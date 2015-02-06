kakaotalk-analyzer
==================

Litte Python script to get statistics from KakaoTalk message export files.

This is totally work-in-progress, but I will try to only put at
least kind of functional versions up on GitHub.

Last tested with KakaoTalk version 4.5.2

Feedback
--------

Feedback and pull requests very welcome! You can also create issues if you have ideas
for analysis I could add.

How to export messages
----------------------

- In the app, go to a chatroom and select Settings (설정) -> Export Messages (대화내용 이메일로 보내기) -> Send Text Messages Only (텍스트 메시지만 보내기)
- Send the export to your own email account and save the files in some folder.

Usage
-----

Open a console and run `python kakaotalk.py path-to-file.txt action [period]`

KakaoTalk splits export files after 1MB. The tool will automatically find the other parts,
you just need to read in the first file.

Run `python kakaotalk.py` to see available options.

Example output
--------------
![Example plot](http://f.cl.ly/items/1r0C1l2G1C1P0c1w2x1t/Screen%20Shot%202015-02-06%20at%2018.35.13.png)