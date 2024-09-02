import ast
import json
import time
import gym
import requests
from bs4 import BeautifulSoup

# import wikipedia

def clean_str(p):
  return p.encode().decode("unicode-escape").encode("latin1").decode("utf-8")
  # 通过多次编码和解码操作来清理字符串，最终返回一个UTF-8编码的字符串。

class textSpace(gym.spaces.Space):
  def contains(self, x) -> bool:
    """Return boolean specifying if x is a valid member of this space."""
    # 判断 x 是否是这个空间中的有效成员，返回布尔值。
    return isinstance(x, str)
    # 如果 x 是字符串类型，则返回 True，否则返回 False。


class WikiEnv(gym.Env):

  def __init__(self):
    """
      Initialize the environment.
      初始化环境
    """
    super().__init__()
    self.page = None  # 当前的Wikipedia页面
    self.obs = None  # 当前的观察值
    self.lookup_keyword = None  # 当前查找的关键字
    self.lookup_list = None  # 包含当前查找关键字的段落列表
    self.lookup_cnt = None  # 当前查找的索引
    self.steps = 0  # 当前步骤数
    self.answer = None  # 来自智能体的当前答案
    self.observation_space = self.action_space = textSpace()  # 定义观察空间和动作空间为textSpace类型
    self.search_time = 0  # 记录搜索时间
    self.num_searches = 0  # 记录搜索次数

  def _get_obs(self):
    return self.obs  # 返回当前的观察值

  def _get_info(self):
    return {"steps": self.steps, "answer": self.answer}  # 返回当前步骤数和答案信息

  def reset(self, seed=None, return_info=False, options=None):
    # We need the following line to seed self.np_random
    # 下面这一行可以用于为self.np_random设置种子
    # super().reset(seed=seed)
    self.obs = ("Interact with Wikipedia using search[], lookup[], and "
                "finish[].\n")  # 初始化观察值为交互提示信息
    self.page = None  # 重置当前页面
    self.lookup_keyword = None  # 重置查找关键字
    self.lookup_list = None  # 重置包含关键字的段落列表
    self.lookup_cnt = None  # 重置查找索引
    self.steps = 0  # 重置步骤计数
    self.answer = None  # 重置答案
    observation = self._get_obs()  # 获取当前观察值
    info = self._get_info()  # 获取当前信息
    return (observation, info) if return_info else observation  # 根据参数返回观察值和信息

  def construct_lookup_list(self, keyword):
    # find all paragraphs
    # 找到所有段落
    if self.page is None:
      return []  # 如果页面为空，返回空列表
    paragraphs = self.page.split("\n")  # 通过换行符分割页面内容
    paragraphs = [p.strip() for p in paragraphs if p.strip()]  # 去除空白段落

    # find all sentences
    # 找到所有句子
    sentences = []
    for p in paragraphs:
      sentences += p.split('. ')  # 通过句号分割段落为句子
    sentences = [s.strip() + '.' for s in sentences if s.strip()]  # 去除空白句子并加上句号

    parts = sentences
    parts = [p for p in parts if keyword.lower() in p.lower()]  # 找到包含关键字的句子
    return parts  # 返回包含关键字的句子列表

  @staticmethod
  def get_page_obs(page):
    # find all paragraphs
    # 找到所有段落
    paragraphs = page.split("\n")  # 通过换行符分割页面内容
    paragraphs = [p.strip() for p in paragraphs if p.strip()]  # 去除空白段落

    # find all sentences
    # 找到所有句子
    sentences = []
    for p in paragraphs:
      sentences += p.split('. ')  # 通过句号分割段落为句子
    sentences = [s.strip() + '.' for s in sentences if s.strip()]  # 去除空白句子并加上句号
    return ' '.join(sentences[:5])  # 返回前五个句子组成的字符串

    # ps = page.split("\n")
    # ret = ps[0]
    # for i in range(1, len(ps)):
    #   if len((ret + ps[i]).split(" ")) <= 50:
    #     ret += ps[i]
    #   else:
    #     break
    # return ret
    # 以上代码是注释掉的备用方法，用于根据单词数来获取摘要

  def search_step(self, entity):
    entity_ = entity.replace(" ", "+")  # 将实体名称中的空格替换为加号，用于生成搜索URL
    search_url = f"https://en.wikipedia.org/w/index.php?search={entity_}"  # 生成Wikipedia搜索URL
    old_time = time.time()  # 记录当前时间，用于计算搜索时间
    response_text = requests.get(search_url).text  # 发送请求并获取响应文本
    self.search_time += time.time() - old_time  # 计算搜索耗时并累加到总搜索时间中
    self.num_searches += 1  # 搜索次数加一
    soup = BeautifulSoup(response_text, features="html.parser")  # 使用BeautifulSoup解析HTML
    result_divs = soup.find_all("div", {"class": "mw-search-result-heading"})  # 查找搜索结果的标题部分
    if result_divs:  # 如果有搜索结果，但与搜索关键词不完全匹配
      self.result_titles = [clean_str(div.get_text().strip()) for div in result_divs]  # 清理并提取结果标题
      self.obs = f"Could not find {entity}. Similar: {self.result_titles[:5]}."  # 更新观察值，提示类似结果
    else:
      page = [p.get_text().strip() for p in soup.find_all("p") + soup.find_all("ul")]  # 提取页面中的段落和列表内容
      if any("may refer to:" in p for p in page):  # 如果页面提示可能的参考内容
        self.search_step("[" + entity + "]")  # 递归搜索更加精确的关键词
      else:
        self.page = ""  # 初始化页面内容为空字符串
        for p in page:
          if len(p.split(" ")) > 2:  # 只添加包含超过两个单词的段落
            self.page += clean_str(p)  # 清理并添加段落
            if not p.endswith("\n"):  # 如果段落不以换行结束，手动添加换行符
              self.page += "\n"
        self.obs = self.get_page_obs(self.page)  # 获取页面的前几句作为观察值
        self.lookup_keyword = self.lookup_list = self.lookup_cnt = None  # 重置查找相关的变量

  def step(self, action):
    reward = 0  # 初始化奖励为0
    done = False  # 初始化done标志为False，表示任务未完成
    action = action.strip()  # 去除动作字符串两端的空白
    if self.answer is not None:  # 如果答案已经确定
      done = True  # 设置done为True，表示任务完成
      return self.obs, reward, done, self._get_info()  # 返回当前观察值、奖励、任务完成标志和信息

    if action.startswith("search[") and action.endswith("]"):
      entity = action[len("search["):-1]  # 提取search[]中的实体名称
      # entity_ = entity.replace(" ", "_")
      # search_url = f"https://en.wikipedia.org/wiki/{entity_}"
      # 注释掉的备用方法，用于直接跳转到Wikipedia页面
      self.search_step(entity)  # 执行搜索步骤
    elif action.startswith("lookup[") and action.endswith("]"):
      keyword = action[len("lookup["):-1]  # 提取lookup[]中的关键字
      if self.lookup_keyword != keyword:  # 如果查找的关键字发生了变化
        self.lookup_keyword = keyword  # 更新查找关键字
        self.lookup_list = self.construct_lookup_list(keyword)  # 构造包含关键字的句子列表
        self.lookup_cnt = 0  # 重置查找索引
      if self.lookup_cnt >= len(self.lookup_list):  # 如果查找索引超出范围
        self.obs = "No more results.\n"  # 提示没有更多结果
      else:
        self.obs = f"(Result {self.lookup_cnt + 1} / {len(self.lookup_list)}) " + self.lookup_list[
          self.lookup_cnt]  # 返回当前查找到的结果
        self.lookup_cnt += 1  # 查找索引加一
    elif action.startswith("finish[") and action.endswith("]"):
      answer = action[len("finish["):-1]  # 提取finish[]中的答案
      self.answer = answer  # 保存答案
      done = True  # 设置done为True，表示任务完成
      self.obs = f"Episode finished, reward = {reward}\n"  # 更新观察值为任务完成提示
    elif action.startswith("think[") and action.endswith("]"):
      self.obs = "Nice thought."  # 如果动作是think[]，返回思考的提示
    else:
      self.obs = "Invalid action: {}".format(action)  # 如果动作无效，返回无效动作提示

    self.steps += 1  # 步骤计数加一

    return self.obs, reward, done, self._get_info()  # 返回当前观察值、奖励、任务完成标志和信息

  def get_time_info(self):
    speed = self.search_time / self.num_searches if self.num_searches else 0  # 计算平均搜索时间
    return {
      "call_speed": speed,  # 返回平均搜索时间
      "call_time": self.search_time,  # 返回总搜索时间
      "num_calls": self.num_searches,  # 返回搜索次数
    }  # 返回搜索时间信息字典
