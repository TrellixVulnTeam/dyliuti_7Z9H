import pickle
import json


STATES = {'B', 'M', 'E', 'S'}
EPS = 0.0001
# 定义停顿标点
seg_stop_words = {" ","，","。","“","”",'“', "？", "！", "：", "《", "》", "、", "；", "·", "‘ ", "’", "──", ",", ".", "?", "!", "`", "~", "@", "#", "$", "%", "^", "&", "*", "(", ")", "-", "_", "+", "=", "[", "]", "{", "}", '"', "'", "<", ">", "\\", "|" "\r", "\n","\t"}

class HMM_Model:
	def __init__(self):
		self.trans_mat = {}
		self.emit_mat = {}
		self.init_vec = {}
		self.state_count = {}
		self.states = {}
		self.inited = False
	# 初始化
	def setup(self):
		for state in self.states:
			# build trans_mat
			self.trans_mat[state] = {}
			for target in self.states:
				self.trans_mat[state][target] = 0.0
			self.emit_mat[state] = {}
			self.init_vec[state] = 0
			self.state_count[state] = 0
		self.inited = True
	# 模型保存
	def save(self, filename, code):
		fw = open(filename, 'w', encoding='utf-8')
		data = {
			"trans_mat": self.trans_mat,
			"emit_mat": self.emit_mat,
			"init_vec": self.init_vec,
			"state_count": self.state_count
		}
		if code == "json":
			txt = json.dumps(data)
			txt = txt.encode('utf-8').decode('unicode-escape')
			fw.write(txt)
		elif code == "pickle":
			pickle.dump(data, fw)
		fw.close()
	#模型加载
	def load(self, filename, code):
		fr = open(filename, 'r', encoding='utf-8')
		if code == "json":
			txt = fr.read()
			model = json.loads(txt)
		elif code == "pickle":
			model = pickle.load(fr)
		self.trans_mat = model["trans_mat"]
		self.emit_mat = model["emit_mat"]
		self.init_vec = model["init_vec"]
		self.state_count = model["state_count"]
		self.inited = True
		fr.close()
	#模型训练
	def do_train(self, observes, states):
		if not self.inited:
			self.setup()

		for i in range(len(states)):
			if i == 0:
				self.init_vec[states[0]] += 1
				self.state_count[states[0]] += 1
			else:
				self.trans_mat[states[i - 1]][states[i]] += 1
				self.state_count[states[i]] += 1
				if observes[i] not in self.emit_mat[states[i]]:
					self.emit_mat[states[i]][observes[i]] = 1
				else:
					self.emit_mat[states[i]][observes[i]] += 1
	#HMM计算
	def get_prob(self):
		init_vec = {}
		trans_mat = {}
		emit_mat = {}
		default = max(self.state_count.values())

		for key in self.init_vec:
			if self.state_count[key] != 0:
				init_vec[key] = float(self.init_vec[key]) / self.state_count[key]
			else:
				init_vec[key] = float(self.init_vec[key]) / default

		for key1 in self.trans_mat:
			trans_mat[key1] = {}
			for key2 in self.trans_mat[key1]:
				if self.state_count[key1] != 0:
					trans_mat[key1][key2] = float(self.trans_mat[key1][key2]) / self.state_count[key1]
				else:
					trans_mat[key1][key2] = float(self.trans_mat[key1][key2]) / default

		for key1 in self.emit_mat:
			emit_mat[key1] = {}
			for key2 in self.emit_mat[key1]:
				if self.state_count[key1] != 0:
					emit_mat[key1][key2] = float(self.emit_mat[key1][key2]) / self.state_count[key1]
				else:
					emit_mat[key1][key2] = float(self.emit_mat[key1][key2]) / default
		return init_vec, trans_mat, emit_mat
	#模型预测
	def do_predict(self, sequence):
		tab = [{}]
		path = {}
		init_vec, trans_mat, emit_mat = self.get_prob()

		# 初始化
		for state in self.states:
			tab[0][state] = init_vec[state] * emit_mat[state].get(sequence[0], EPS)
			path[state] = [state]

		# 创建动态搜索表
		for t in range(1, len(sequence)):
			tab.append({})
			new_path = {}
			for state1 in self.states:
				items = []
				for state2 in self.states:
					if tab[t - 1][state2] == 0:
						continue
					prob = tab[t - 1][state2] * trans_mat[state2].get(state1, EPS) * emit_mat[state1].get(sequence[t],
																										  EPS)
					items.append((prob, state2))
				best = max(items)
				tab[t][state1] = best[0]
				new_path[state1] = path[best[1]] + [state1]
			path = new_path

		# 搜索最有路径
		prob, state = max([(tab[len(sequence) - 1][state], state) for state in self.states])
		return path[state]


def get_tags(src):
	tags = []
	if len(src) == 1:
		tags = ['S']
	elif len(src) == 2:
		tags = ['B', 'E']
	else:
		m_num = len(src) - 2
		tags.append('B')
		tags.extend(['M'] * m_num)
		tags.append('E')
	return tags

def cut_sent(src, tags):
	word_list = []
	start = -1
	started = False

	if len(tags) != len(src):
		return None

	if tags[-1] not in {'S', 'E'}:
		if tags[-2] in {'S', 'E'}:
			tags[-1] = 'S'
		else:
			tags[-1] = 'E'

	for i in range(len(tags)):
		if tags[i] == 'S':
			if started:
				started = False
				word_list.append(src[start:i])
			word_list.append(src[i])
		elif tags[i] == 'B':
			if started:
				word_list.append(src[start:i])
			start = i
			started = True
		elif tags[i] == 'E':
			started = False
			word = src[start:i+1]
			word_list.append(word)
		elif tags[i] == 'M':
			continue
	return word_list

class HMM_FenCi(HMM_Model):
	def __init__(self, *args, **kwargs):
		super(HMM_FenCi, self).__init__(*args, **kwargs)
		self.states = STATES
		self.data = None
	#加载训练数据
	def read_txt(self, filename):
		self.data = open(filename, 'r', encoding="utf-8")
	#模型训练函数
	def train(self):
		if not self.inited:
			self.setup()

		for line in self.data:
			line = line.strip()
			if not line:
				continue

			# 观测序列
			observes = []
			for i in range(len(line)):
				if line[i] == " ":
					continue
				observes.append(line[i])

			# 状态序列
			words = line.split(" ")

			states = []
			for word in words:
				if word in seg_stop_words:
					continue
				states.extend(get_tags(word))
			# 开始训练
			if (len(observes) >= len(states)):
				self.do_train(observes, states)
			else:
				pass
	#模型分词预测
	def lcut(self, sentence):
		try:
			tags = self.do_predict(sentence)
			return cut_sent(sentence, tags)
		except:
			return sentence


FenCi = HMM_FenCi()
FenCi.read_txt("Data/NLP/Chinese/syj_trainCorpus_utf8.txt")
FenCi.train()

FenCi.lcut("中国的人工智能发展进入高潮阶段。")
FenCi.lcut("中文自然语言处理是人工智能技术的一个重要分支。")