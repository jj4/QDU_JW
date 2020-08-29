# -*- coding: utf-8 -*-
import re, requests, requests.utils, pytesseract, time, json
from PIL import Image
from lxml import etree
from prettytable import PrettyTable


# tesseract 识别验证码
def ocr(path):
    image = Image.open(path).convert('L')  # 打开图片文件 转化为灰度图
    # 获取灰度转二值的映射table
    table = []
    for i in range(256):  # 二值化处理 阈值131
        if i < 131:
            table.append(0)
        else:
            table.append(1)
    binary = image.point(table, '1')
    # 仅识别数字
    text = pytesseract.image_to_string(binary, config='digits')
    # 去掉特殊字符
    exclude_char_list = ' .:\\|\'\"?![],()~@#$%^&*_+-={};<>/¥'
    text = ''.join([x for x in text if x not in exclude_char_list])
    return text


class qdujw:
    def __init__(self):
        self.s = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/83.0.4103.116 Safari/537.36 '
        }
        self.url = {
            'login': 'http://jw.qdu.edu.cn/academic/j_acegi_security_check',
            'login_captcha': 'http://jw.qdu.edu.cn/academic/getCaptcha.do',
            'login_check': 'http://jw.qdu.edu.cn/academic/checkCaptcha.do',
            'head_info': 'http://jw.qdu.edu.cn/academic/showHeader.do',
            'scores': 'http://jw.qdu.edu.cn/academic/manager/score/studentOwnScore.do',
            'select': 'http://jw.qdu.edu.cn/academic/manager/electcourse/electiveSelectCourseAdd.do',
            'select_captcha': 'http://jw.qdu.edu.cn/academic/manager/electcourse/getCaptcha.do',
            'select_check': 'http://jw.qdu.edu.cn/academic/manager/electcourse/checkCaptcha.do',
            'user': 'http://jw.qdu.edu.cn/academic/student/studentinfo/studentInfoModifyIndex.do',
            'timetable': 'http://jw.qdu.edu.cn/academic/manager/coursearrange/showTimetable.do',
            'credit': 'http://jw.qdu.edu.cn/academic/student/queryscore/check.jsdo'
        }
        # 登录数据
        self.jw_data = {
            'j_username': '',
            'j_password': '',
            'j_captcha': ''
        }

    # 获取登录验证码
    def get_captcha(self):
        captcha_page = self.s.get(self.url['login_captcha'], headers=self.headers).content
        # 保存为code.jpg，'b'二进制写方式，用content来获得bytes格式
        with open('./login_captcha.jpg', 'wb') as f:
            f.write(captcha_page)

    # 识别 校验登录验证码
    def check_captcha(self):
        self.get_captcha()
        code = ocr('./login_captcha.jpg')
        # print(code)
        check = self.s.get(self.url['login_check'], headers=self.headers, params={'captchaCode': code})
        # 调用接口，判断验证码是否正确
        print('登录中... 请稍后...')
        if check.json():
            self.jw_data['j_captcha'] = code
        else:
            self.check_captcha()

    # 获取Cookie
    def get_cookie(self):
        self.check_captcha()
        # 到这里验证码一定是正确的 如果账号密码正确则登录成功
        self.s.post(self.url['login'], headers=self.headers, data=self.jw_data)
        # 保存Cookie
        cookies = requests.utils.dict_from_cookiejar(self.s.cookies)
        with open("./cookie.json", "w") as fp:
            json.dump(cookies, fp)

        head_page = self.s.get(self.url['head_info'])
        name = etree.HTML(head_page.content).xpath('//*[@id="greeting"]/span/text()')[0]
        print(name + '登录成功！')

    # 登录入口
    def login(self):
        # 读取cookie
        with open("./cookie.json", "r") as fp:
            load_cookies = json.load(fp)
        # 添加Cookie
        self.s.cookies = requests.utils.cookiejar_from_dict(load_cookies)
        head_page = self.s.get(self.url['head_info'], allow_redirects=False)  # 禁止重定向处理
        try:
            name = etree.HTML(head_page.content).xpath('//*[@id="greeting"]/span/text()')[0]
            print(name + '登录成功！')
        except AttributeError:
            print("Cookie失效 正在重新登录...")
            self.get_cookie()

    # 查成绩
    def scores(self):
        print('---------- 个人成绩查询 ----------')
        year = input('请输入查询学年: ')
        term = input('春季学期输入[1], 秋季学期输入[2], 夏季学期输入[3]: ')
        # 字符串计算  eval()
        postdata = {
            'year': eval(year + '-' + '1980'),
            'term': term,
            'para': '0'
        }
        scores_page = self.s.post(self.url['scores'], headers=self.headers, data=postdata).text
        # 去除空格 空行 换行
        scores_page = scores_page.replace('\n', '').replace('\r', '').replace(' ', '').replace('&nbsp;', '')
        regex = '<td>' + year + '.*?<td>.*?</td>.*?<td>.*?</td>.*?<td>.*?</td>.*?<td>(.*?)</td>.*?<td>.*?</td>.*?<td>.*?</td>.*?<td>.*?</td>.*?<td>.*?</td>.*?<td>(.*?)</td>'
        # 正则...
        scores = re.findall(regex, scores_page)
        print('---------- 考试成绩 ----------')
        for score in scores:
            print(score[0] + ': ' + score[1])

    # 选课系统1 非选课期间无效
    def elect(self, pcourseid, seq):
        # 获取选课验证码
        captcha_page = self.s.get(self.url['select_captcha'], headers=self.headers).content
        with open('./select_captcha.jpg', 'wb') as f:
            f.write(captcha_page)
        # 识别验证码
        code = ocr('./select_captcha.jpg')
        check = self.s.post(self.url['select_check'], headers=self.headers, params={'captchaCode': code})
        # 调用接口，判断验证码是否正确
        if not check.json():
            # 验证码错误
            print('选课中...')
            self.elect(pcourseid, seq)
        else:
            # 验证码正确
            course = {
                'pcourseid': pcourseid,  # 课程号
                'seq': seq,  # 课序号
                '_': int(round(time.time() * 1000))  # 时间戳
            }
            try:
                elect_page = self.s.get(self.url['select'], headers=self.headers, params=course).json()
                coursename = elect_page["result"]["coursename"]
                message = elect_page["result"]["message"]
                print(coursename, message)
            except ValueError:
                print("现在不能选课！")

    # 选课系统2 可一次选多门专业限选课
    def select(self, courselist):
        # 获取选课验证码
        captcha_page = self.s.get(self.url['select_captcha'], headers=self.headers).content
        with open('./select_captcha.jpg', 'wb') as f:
            f.write(captcha_page)
        code = ocr('./select_captcha.jpg')
        check = self.s.post(self.url['select_check'], headers=self.headers, params={'captchaCode': code})
        # 调用接口，判断验证码是否正确
        if not check.json():
            # 验证码错误
            print('选课中...')
            self.select(courselist)
        else:
            # 验证码正确
            course_list = {
                'epid': courselist,
                '_': int(round(time.time() * 1000))  # 时间戳
            }
            try:
                select_page = self.s.get(self.url['select'], headers=self.headers, params=course_list).json()
                # print(select_page)
                tplt = "{0:{3}^10}\t{1:{3}^10}\t{2:^10}"
                for item in select_page["resultList"]:
                    print("{:15}\t{:15}\t{:30}".format(item['pcourseid'], item['coursename'], item['message']))
            except ValueError:
                print("现在不能选课！")

    def timetable(self):
        print('---------- 课表查询 ----------')
        year = input('请输入查询学年: ')
        term = input('春季学期输入[1], 秋季学期输入[2], 夏季学期输入[3]: ')
        # 带参数才能正常显示学籍信息 userid不用
        showdata = {
            'frombase': '0',
            'wantTag': '0'
        }
        # 获取userid
        user_page = self.s.get(self.url['user']).content
        userid = etree.HTML(user_page).xpath('//*[@name="stuUserId"]/@value')[0]
        # 使用 PrettyTable 打印表格
        x = PrettyTable(["周一", "周二", "周三", "周四", "周五", "周六", "周日"])
        x.padding_width = 1
        getdata = {
            'id': userid,
            'yearid': eval(year + '-' + '1980'),
            'termid': term,
            'timetableType': 'STUDENT',
            'sectionType': 'COMBINE'  # 大节课表
            # 'sectionType' = 'BASE'  # 小节课表
        }
        kb_page = self.s.get(self.url['timetable'], params=getdata)
        # params是添加到url的请求字符串中的 用于get请求
        kb = etree.HTML(kb_page.content).xpath('//*[@id="timetable"]//*[@class="center"]')
        i = 0
        list = []
        list1 = ['', '', '', '', '', '', '']
        for k in kb:
            # 通过 list 将课程信息添加到 PrettyTable 中
            if i < 7:
                list.append(k.text.split(';')[0].replace('<<', '').replace('>>', ''))
                i += 1
                if i == 7:
                    # 上下显示一行空白，方便阅读
                    x.add_row(list1)
                    x.add_row(list)
                    x.add_row(list1)
                    list = []
                    i = 0
        print(x)


if __name__ == '__main__':
    jw = qdujw()  # 同一个session保持cookie
    jw.login()
    while 1:
        print('======== 综合教务管理系统 ========')
        print('[1] 查成绩')
        print('[2] 查课表')
        print('[3] 选  课')
        print('[4] 退  出')
        choice = input('请选择: ')
        if choice == '1':
            jw.scores()
        if choice == '2':
            jw.timetable()
        if choice == '3':
            # 用法示例
            # while 1:
            jw.select('484928711,484922594,485046996,485276973')
            '''
            jw.select('484928711,485046996')
            jw.elect('C06080004017', '1')  # DSP原理及应用
            jw.elect('4471080801018', '1')  # 信号与系统
            jw.elect('C06080004018', '2')  # 控制系统仿真（MATLAB）
            jw.elect('C06080004032', '2')  # 工业控制组态软件
            '''
        if choice == '4':
            exit()
