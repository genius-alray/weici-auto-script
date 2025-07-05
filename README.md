# 维词APP 自动化脚本
<center>
<img style="width: 64px" src="https://pp.myapp.com/ma_icon/0/icon_52654510_1737342498/256">
</center>

使用pyautomator2实现的维词（高中） 自动化脚本。
由于作者没有教师账号，需要根据自己的作业情况来完善脚本，因此不一定能覆盖所有情况

## 支持的题目类型
- [x] 拼写 (支持大小写切换和连字符)
- [x] 单选
- [x] 选词填空
- [x] 前后缀填空
- [ ] ~~听力~~ （不会实现）

## 特色
- 支持通过配置文件批量运行多个账号
- 可配置模拟每题思考时间（随机等待），控制正确率（随机出错）
- 出现异常时自动重启（遇到未知题目除外）

## 使用方法
1. 创建虚拟环境并根据`requirements.txt`安装所需依赖，推荐使用`uv`

```shell
uv venv
#自行激活venv
uv pip install -r requirements.txt
```

2. 在`main.py`同级位置创建`config.toml`,并配置用户和adb地址

```toml
adb_address = "127.0.0.1:16384" # 此处是mumu12模拟器的默认地址, 其他模拟器或真机清自行查找


[[user]]
username = "手机号"
password = "密码"
nickname = "小明" #对应登录账号后在'我的'页面显示的昵称
accuracy = 0.9 # 正确率 运行过程中会有 (1-accuracy)*100% 的概率引入随机错误
average_time = 1.5 # 平均每题所用时间
time_random = 0.5 # 时间随机范围, 等待时间 = average_time ± time_random

[[user]]
username = "手机号"
password = "密码"
nickname = "xxx"
accuracy = 0.8
average_time = 3.0
time_random = 0.5

# ... 可添加更多[[user]]字段
```

3. 运行`main.py`
```shell
python main.py
```

## 注意事项
- 由于某些特殊原因,请勿在脚本运行过程中操作模拟器窗口(包括改变窗口状态 位置,甚至在模拟器窗口内移动鼠标), 有极大概率导致点击失效引发卡死

- 对题目的支持取决于作者遇到的作业,若脚本遇到不支持的题型,会自动停下等待,手动处理后,按任意键可继续

- 若某个单元有做题进度, 进入时程序会优先选择继续进度

## 题库来源
维词作业题目全部储存在本地，在应用私有数据目录`/data/user/0/com.android.weici.senior.student/databases`
中的 `extXXX.db`，数据库内容会随版本更新而发生改变。此目录需要root权限才能访问，推荐使用模拟器提取该文件。



## 贡献
作者本人并不太了解python开发, 脚本代码混乱 ~~纯纯屎山~~, 欢迎提出PR对代码进行整理或者添加对新题型的支持.

目前在test_loop函数中的处理逻辑十分不妥~~程序依靠bug来运行~~,有能力的话,请提出PR改善,万分感谢!
