import spacy
from deta import Deta
from pyclausie import ClausIE
import sys
import threading, json, time
import pymysql
import streamlit

cl = ClausIE.get_instance()
nlp = spacy.load("en_core_web_sm")



# In[ ]:


# 斷句
def sentencizer(text: str) -> list:
    doc = nlp(text)
    return [sent.text for sent in doc.sents]


# In[ ]:


# 詞性還原
def lemmatization(text: str) -> str:
    doc = nlp(text)
    res = ''
    for token in doc:
        res += token.lemma_ + ' '
    return res


# In[106]:


# 詞性過濾
# 如果一段話中僅包含給定的詞性，則回傳False
def pos_filter(text: str) -> bool:
    pos = ['ADP', 'AUX', 'CCONJ', 'DET', 'PART', 'SCONJ', 'SPACE', 'PUNCT', 'SYM', 'X', 'DET']
    self_pos = []
    self_token = []
    doc = nlp(text)
    res = ''
    for token in doc:
        if token.text in ['the', 'a', 'this', 'all', 'some', 'any', 'no']:
            self_pos.append('DET')
        else:
            self_pos.append(token.pos_)
    # if self_pos only has pos in pos, return False
    if set(self_pos).issubset(set(pos)):
        return False
    else:
        return True


# In[ ]:


# 使用clausie進行句法分析
def get_triple(inpu: str) -> list:
    if type(inpu).__name__ == 'str':
        inpu = [inpu]
    res = []
    ax = cl.extract_triples(inpu)
    for i in range(len(ax)):
        res.append([ax[i][1].replace('â','a').replace('$ s',"'s"), ax[i][2].replace('â','a').replace('$ s',"'s"), ax[i][3].replace('â','a').replace('$ s',"'s")])
    return res


# In[ ]:


# 將三元組細分
def tri2tri(sour: list, res: list) -> list:
    a, b, c = sour
    have_update = False

    # a
    if len(a.split(' ')) >2: 
        tri = get_triple(a)
        if tri != []:
            for i in tri:
                res.append([i[0],b,c])
                have_update = True
                if [a,b,c] in res:
                    res.remove([a,b,c])



    # c
    if len(c.split(' ')) >2: 
        tri = get_triple(c)
        if tri != []:
            for i in tri: 
                res.append([a,b,i[0]])
                res.append(i)
                have_update = True
                if [a,b,c] in res:
                    res.remove([a,b,c]) 

    
    # check if res has repeat
    res = list(set([tuple(t) for t in res]))
    res = [list(t) for t in res]
    return res, have_update



# In[118]:


# 在句子中去掉特定詞性
def remove_pos(text: str) -> str:
    pos = ['ADV','ADP',  'DET', 'PART', 'SCONJ',  'PUNCT', 'SYM', 'X']
    self_pos = []
    self_token = []
    doc = nlp(text)
    res = ''
    for token in doc:
        self_token.append(token.text)
        if token.text in ['the', 'a', 'this', 'all', 'some', 'any', 'no', '\\', '!!']:
            self_pos.append('DET')
        else:
            self_pos.append(token.pos_)
    for i in range(len(self_pos)):
        if self_pos[i] not in pos :
            # print(self_pos[i])
            res += doc[i].text + ' '
    return res

remove_pos('Wall Street Journal ')


# In[133]:


def text2triple(data: list) -> list:
    text = data
    sents = sentencizer(text)
    resul = []
    for text in sents:
        trips = get_triple(text)
        if trips != []:
            a = trips

            # 重複運算
            state = True
            while state:
                for i in a:
                    a, state = tri2tri(i, a)

            # 清除不合格的三元組
            trip = a
            for i in trip:
                if not pos_filter(i[0]) or not pos_filter(i[2]):
                    trip.remove(i)
            trip = list(set([tuple(t) for t in trip]))
            trip = [list(t) for t in trip]
            # 整理三元組
            trip_ = trip
            for i in range(len(trip_)):
                for r in range(len(trip_[i])):
                    trip_[i][r] = remove_pos(trip_[i][r])
            for i in range(len(trip_)):
                try:    # 已經被刪出故無法再刪
                    if trip_[i][0] == '' or trip_[i][2] == '':
                        trip_.remove(trip_[i])
                except:
                    pass
            for i in range(len(trip_)):
                try:
                    for r in range(len(trip_[i])):
                    
                        if trip_[i][r] == '':
                            trip_.remove(trip_[i])
                            break
                        trip_[i][r] = lemmatization(trip_[i][r])
                except:
                        pass
            resul += trip_
        
    resul = list(set([tuple(t) for t in resul]))
    resul = [list(t) for t in resul]
    return resul



while True:
    
    try:
        sys.stdout.write('statr')
        threads = []
        conn = pymysql.connect(host='db-mysql-nyc1-54982-do-user-12664850-0.b.db.ondigitalocean.com', port=25060, user='doadmin', passwd='AVNS_b83V99ApzBOgDm3qIHI', db='defaultdb', charset='utf8')
        c = conn.cursor()

        st_time = time.time()
        c.execute("SELECT * FROM `train` WHERE `triple` = '' LIMIT 1")
        data = c.fetchall()[0]
        conn.close()
        print(data)

        id, summary = data[0], data[1]
        conn = pymysql.connect(host='db-mysql-nyc1-54982-do-user-12664850-0.b.db.ondigitalocean.com', port=25060, user='doadmin', passwd='AVNS_b83V99ApzBOgDm3qIHI', db='defaultdb', charset='utf8')
        c = conn.cursor()
        c.execute(f"UPDATE `train` SET `triple` = 'processing' WHERE `id` = {id}")
        conn.commit()
        conn.close()
        triple = text2triple(summary)
        print(f"UPDATE `train` SET `triple` = {triple} WHERE `id` = {id}")
        conn = pymysql.connect(host='db-mysql-nyc1-54982-do-user-12664850-0.b.db.ondigitalocean.com', port=25060, user='doadmin', passwd='AVNS_b83V99ApzBOgDm3qIHI', db='defaultdb', charset='utf8')
        c = conn.cursor()
        c.execute('update `train` set `triple` = %s where `id` = %s', (str(triple), id))
        conn.commit()
        conn.close()
        end_time = time.time()
        sys.stdout.write(f'\r{end_time-st_time}')
    except:
        pass


    
    