import os
import subprocess

# 指定工作目录


# 执行命令


main_dir_name = r'D:\爬虫新\porn_sex'
original_directory = os.getcwd()

for dir_name in os.listdir(main_dir_name):
    sec_dir = os.path.join(main_dir_name, dir_name)
    for k in os.listdir(sec_dir):
        th_dir = os.path.join(sec_dir, k)
        if os.path.isdir(th_dir):
            tsl = []
            for ts in os.listdir(th_dir):
                if ts.endswith('ts'):
                    ts_dir = os.path.join(th_dir, ts)
                    tsl.append(ts_dir)

            target = os.path.join(th_dir, 'output.mp4')
            work_dir = main_dir_name
            os.chdir(work_dir)
            cmd = f'ffmpeg -i "concat:{"|".join(tsl)}" -c copy {target}'
            subprocess.run(cmd, shell=True)
            os.chdir(original_directory)






