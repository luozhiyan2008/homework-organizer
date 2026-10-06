\# homework-organizer 作业文件批量归档脚本



用 Python 写的命令行小工具，把文件夹里「学号\_姓名\_作业名」格式的作业文件自动整理归档。



\## 功能（4 个子命令）



\- scan：扫描文件夹，列出作业文件，可按扩展名过滤

\- rename：批量改作业名，先打印计划，确认后才执行

\- archive：把文件归档到子文件夹，并生成「整理报告.txt」

\- undo：撤销上一次改名/归档，文件全部还原



\## 安全设计



\- 改名、归档、撤销执行前都先打印计划，输入 y 确认才动手

\- 目标文件已存在时自动跳过，绝不覆盖

\- 操作记录保存在 .organize\_log.json，undo 按记录反向执行



\## 用法



python organize.py <子命令> <文件夹路径>

例如：python organize.py scan D:\\test-homework



\## 环境



Python 3.10+，无需安装任何第三方库。

