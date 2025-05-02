import logging
import time
from retry import retry
import uiautomator2 as u2
from dataclasses import dataclass, field
from uiautomator2 import Direction
from enum import Enum
import sqlite3
import re
import random
import tomllib
import os
from datetime import datetime
from colorama import Fore, Style, init

# 初始化colorama
init(autoreset=True)


# 配置日志
def setup_logger():
    # 创建logs目录（如果不存在）
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # 创建logger实例
    logger = logging.getLogger("AutoWeici")
    logger.setLevel(logging.DEBUG)

    class ColoredFormatter(logging.Formatter):
        COLORS = {
            "DEBUG": Fore.CYAN,
            "INFO": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.RED + Style.BRIGHT,
        }

        def format(self, record):
            if record.levelname in self.COLORS:
                levelname = f"{self.COLORS[record.levelname]}{record.levelname}{Style.RESET_ALL}"
                msg = f"{self.COLORS[record.levelname]}{record.msg}{Style.RESET_ALL}"
                record.levelname = levelname
                record.msg = msg
            return super().format(record)

    console_formatter = ColoredFormatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG)

    # 文件处理器
    log_filename = f'logs/{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)

    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# 设置日志
logger = setup_logger()

# 读取配置文件
with open("config.toml", "rb") as f:
    config = tomllib.load(f)

db = sqlite3.connect("weici.db")


class QuestionType(Enum):
    SPELLING = "拼写"
    SINGLE_CHOICE = "单选"


@dataclass
class Automation:
    username: str
    password: str
    nickname: str
    accuracy: float = 0.9
    average_time: float = 3
    time_random: float = 1
    skipped: bool = False

    @retry(logger=logger, delay=10)
    def __post_init__(self):
        if self.skipped:
            return
        self.d = u2.connect(config["adb_address"])
        self.d.app_stop("com.android.weici.senior.student")
        self.d.app_start("com.android.weici.senior.student")
        self.watcher_context = self.d.watch_context()
        self.watcher_context.when("不再提醒").click()
        self.watcher_context.when("重来").when("继续").click()
        self.watcher_context.when(
            '//*[@resource-id="com.android.weici.senior.student:id/obtain_revivecard_dialog_close"]'
        ).click()
        self.start()
        self.watcher_context.close()

    def handle_login(self):
        logger.info("开始登录")
        self.click_by_resourceId("com.android.weici.senior.student:id/text2")
        self.click_by_resourceId(
            "com.android.weici.senior.student:id/login_edit_mobile"
        )
        self.d.send_keys(self.username, True)
        self.click_by_resourceId("com.android.weici.senior.student:id/pwd")
        self.d.send_keys(self.password, True)
        self.click_by_resourceId("com.android.weici.senior.student:id/btn_login")
        self.click_by_resourceId("com.android.weici.senior.student:id/positiveButton")
        self.watcher_context.wait_stable()
        logger.info("登录成功")

    def click_by_resourceId(self, resourceId):
        self.d(resourceId=resourceId).click()

    def start(self):
        logger.info(f"开始启动，目标用户昵称：{self.nickname}")

        self.click_by_resourceId("com.android.weici.senior.student:id/bottom_btn4")
        self.d(resourceId="com.android.weici.senior.student:id/head").wait()
        if self.d(
            resourceId="com.android.weici.senior.student:id/no_login_text"
        ).exists():
            logger.info("未登录")
            self.click_by_resourceId(
                "com.android.weici.senior.student:id/no_login_text"
            )
            self.handle_login()
        else:
            nickname = self.d(
                resourceId="com.android.weici.senior.student:id/nick_name"
            ).get_text()
            logger.info(f"已登录，当前用户昵称：{nickname}")
            if nickname != self.nickname:
                logger.info("与目标账号不符，切换账号")
                self.d.swipe_ext(Direction.FORWARD)
                self.d(text="更多").click()
                self.click_queue(
                    [
                        "com.android.weici.senior.student:id/login_out",
                        "com.android.weici.senior.student:id/positiveButton",
                    ]
                )
                self.handle_login()
        self.click_by_resourceId("com.android.weici.senior.student:id/bottom_btn1")
        self.d(
            resourceId="com.android.weici.senior.student:id/ui_item_text", text="练习"
        ).click()
        self.d(text="练习列表").wait()
        self.walk_units()

    def walk_units(self):
        logger.info("开始遍历练习列表")

        scroll_count = 0
        while True:
            listview = self.d(resourceId="com.android.weici.senior.student:id/listview")
            detected = False
            for count_label in listview.child(
                resourceId="com.android.weici.senior.student:id/all_count"
            ):
                name = count_label.sibling(
                    resourceId="com.android.weici.senior.student:id/tv_name"
                ).get_text()
                count_str = count_label.get_text()[5:]
                total = count_str.split("/")
                is_completed = total[0] == total[1]
                logger.debug(f"{name} {count_label.get_text()}")
                if not is_completed:
                    logger.info(f"开始单元：{name}")
                    count_label.click()
                    self.d(text=name).wait()
                    detected = True
                    self.walk_tests()
                    self.d.keyevent("back")
                    break
            if not detected:
                self.d.swipe_ext(Direction.FORWARD)
                scroll_count += 1
                if scroll_count > 3:
                    logger.info("单元遍历完成")
                    return

    def walk_tests(self):
        logger.info("开始遍历测试")
        self.d(text="未提交").wait()
        while self.d(text="未提交").exists():
            logger.info("进入未提交的练习")
            self.d(text="未提交").click()
            self.d(
                text="检测",
                resourceId="com.android.weici.senior.student:id/title_bar_title",
            ).wait()
            self.test_loop()
        logger.info("遍历练习完成")

    def get_now_position(self):
        max = [0, 0]
        for position_label in self.d(
            resourceId="com.android.weici.senior.student:id/position"
        ):
            position = list(map(int, position_label.get_text().split("/")))
            if position[0] > max[0]:
                max = position
        return max

    def test_loop(self):
        last_position = None
        while True:
            last_time = time.time()
            now_position = self.get_now_position()
            if last_position is not None and now_position[1] != last_position[1]:
                last_position = None
                logger.debug("重置位置")
                self.watcher_context.wait_stable()
            if last_position and last_position[0] >= now_position[0]:
                if time.time() - last_time > 5:
                    raise Exception("等待时间过长")
                continue
            logger.debug(f"当前位置：{now_position}")
            last_position = now_position
            selector = self.d(text=f"{now_position[0]}/{now_position[1]}").sibling
            self.random_wait()
            if self.d(text="提交").click_exists():
                logger.info("提交成功")
                return

            question_type = self.detect_question_type(selector)

            if question_type == QuestionType.SPELLING:
                self.handle_spelling(selector)
            elif question_type == QuestionType.SINGLE_CHOICE:
                self.handle_single_choice(selector)
            if now_position[0] == now_position[1]:
                time.sleep(2)
                if self.d(text="去订正").exists() or self.d(text="继续订正").exists():
                    self.d(text="去订正").click_exists()
                    self.d(text="继续订正").click_exists()
                    time.sleep(3)
                    continue

    def random_wait(self):
        value = (
            random.random() * self.time_random * 2
            - self.time_random
            + self.average_time
        )
        logger.debug(f"随机等待：{value}s")
        time.sleep(value)

    def random_fail(self):
        if random.random() > self.accuracy:
            logger.info("引入随机错误")
            return True
        else:
            return False

    def handle_spelling(self, selector):
        logger.info("开始处理拼写")
        chinese_match = re.match(
            r"([a-z]+)\.(.+)",
            selector(
                resourceId="com.android.weici.senior.student:id/chinese"
            ).get_text(),
        )
        yinbiao_match = re.match(
            r"英\[(.+)\]  美\[(.+)\]",
            selector(
                resourceId="com.android.weici.senior.student:id/yinbiao"
            ).get_text(),
        )
        if not chinese_match or not yinbiao_match:
            error_msg = f"文字格式错误 chinese:{chinese_match} yinbiao:{yinbiao_match}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        part_of_speech = chinese_match.group(1)
        chinese = chinese_match.group(2)
        en_phonetic_symbols = yinbiao_match.group(1)
        usa_phonetic_symbols = yinbiao_match.group(2)
        logger.debug(
            f"词性: {part_of_speech} 中文：{chinese} 音标：{en_phonetic_symbols} {usa_phonetic_symbols}"
        )
        # 从数据库查询单词
        word = db.execute(
            "SELECT word FROM fb_word WHERE part_of_speech=? AND chinese=? AND en_phonetic_symbols=? AND usa_phonetic_symbols=?",
            (part_of_speech, chinese, en_phonetic_symbols, usa_phonetic_symbols),
        ).fetchone()[0]
        logger.info(f"从数据库查询到单词: {word}")
        self.virtual_keyboard_input(word)
        self.d(text="下一题").click()

    def handle_single_choice(self, selector):
        logger.info("开始处理单选")
        question = selector(
            resourceId="com.android.weici.senior.student:id/question"
        ).get_text()
        answer_list = selector(
            resourceId="com.android.weici.senior.student:id/answer_list"
        )
        options = []
        for option in answer_list.child(className="android.widget.TextView"):
            options.append(option.get_text())
        logger.debug(f"题目：{question}")
        if self.random_fail():
            logger.info("引入随机错误")
            selector(text=random.choice(options)).click()
            return
        # 从数据库查询答案
        query = """
        SELECT answer FROM fb_word_test 
        WHERE (? IN (substr(answer_a, 4), substr(answer_b, 4), substr(answer_c, 4)))
          AND (? IN (substr(answer_a, 4), substr(answer_b, 4), substr(answer_c, 4)))
          AND (? IN (substr(answer_a, 4), substr(answer_b, 4), substr(answer_c, 4)))
          AND subject=?
        """
        result = db.execute(query, (*options, question)).fetchone()
        logger.debug(f"查询结果：{result}")

        if result:
            answer = result[0]
            logger.info(f"从数据库查询到答案: {answer}")
            # 从options中找到对应的选项文本
            answer_text = next(option for option in options if option in answer)
            selector(text=answer_text).click()
        else:
            logger.warning("未在数据库中找到答案")
            # 随机选择一个答案
            selector(text=random.choice(options)).click()

    def virtual_keyboard_input(self, text: str):
        if self.random_fail():
            text = text[:-1] + "a"
        keyboard = self.d(resourceId="com.android.weici.senior.student:id/keyboard")
        for char in text:
            if char.isupper():
                keyboard.child(
                    resourceId="com.android.weici.senior.student:id/key_shift"
                ).click()
                keyboard.child(text=char).click()
                keyboard.child(
                    resourceId="com.android.weici.senior.student:id/key_shift"
                ).click()
            else:
                keyboard.child(text=char).click()

    def detect_question_type(self, selector):
        if (
            selector(resourceId="com.android.weici.senior.student:id/input").exists()
            and self.d(
                resourceId="com.android.weici.senior.student:id/keyboard"
            ).exists()
        ):
            return QuestionType.SPELLING
        elif selector(
            resourceId="com.android.weici.senior.student:id/answer_list"
        ).exists():
            return QuestionType.SINGLE_CHOICE
        else:
            error_msg = "未知题目类型"
            logger.error(error_msg)
            input("请手动完成，按任意键继续程序")
            # raise ValueError(error_msg)

    def click_queue(self, resourceIds):
        last = resourceIds[-1]
        while True:
            skip = False
            for resourceId in resourceIds:
                if self.d(resourceId=resourceId).click_exists():
                    skip = True
                    if resourceId == last:
                        return
                    break
            if skip:
                continue


# 从配置文件创建自动化实例
logger.info("开始创建自动化实例")
for user_config in config["user"]:
    logger.info(f"创建用户实例：{user_config['nickname']}")
    Automation(**user_config)
