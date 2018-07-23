#coding=utf-8
import requests
import requests.exceptions
from bs4 import BeautifulSoup
import queue
import re
import os
import threading
import datetime
import time

start_time = datetime.datetime.now()

#定义一个通用的下载器，返回html
def html_download(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
    }
    try:
        response = requests.get(url,headers=headers)
        response.encoding = 'gbk'
    except requests.exceptions.HTTPError as e:
        print(e)

    return response.text


#漫画首页的解析，主要是获取这部漫画的名字，和它所有章节的链接，章节链接放入chapter_url队列中
def parse_homepage(url):
    bsObj = BeautifulSoup(url,'lxml')
    comic_name = bsObj.find_all('td',{'colspan':'2'})[6].get_text()     #获取动漫名
    if not os.path.exists('./%s'%comic_name):                           #使用动漫名创建文件夹
        os.mkdir('./%s'%comic_name)
    dd_list = bsObj.find('dl',{'id':'comiclistn'}).find_all('dd')       #获取所有章节的链接，并放入章节链接队列中
    for dd in dd_list:
        chapter_url = dd.find_all('a')[1].attrs['href']
        queue_chapter.put(chapter_url)
    return comic_name                                                   #返回获取的动漫名


#章节解析，主要是获取该章节的页数、章节名字和该章节所有图片的下载url，生成字典并放入pic_mes队列中
def parse_chapter():
    global comic_name
    while not queue_chapter.empty():
        chapter_url = queue_chapter.get(block=True,timeout=3)
        bsObj = BeautifulSoup(html_download(chapter_url),'lxml')

        chapter_mes = bsObj.find_all('table')[1].find('td').get_text()  #获取章节信息（页数，名字）
        chapter_mes = chapter_mes.split('\n')[0].split('|')
        chapter_name = chapter_mes[0].strip()
        page_num = re.search('\d+', chapter_mes[1]).group()

        if not os.path.exists('./%s/%s'%(comic_name,chapter_name)):     #生成章节文件夹
            os.mkdir('./%s/%s'%(comic_name,chapter_name))


        for page in range(int(page_num)):                               #前往每一页漫画的html中寻找图片的下载链接
            url = chapter_url.replace('/1.htm','/%d.htm'%(page+1))
            bsObj = BeautifulSoup(html_download(url),'lxml')


            text = bsObj.find_all('script')[3].get_text()
            pic_url = 'http://n5.1whour.com/' + re.search('\+(.*?)\+"(.*?\.jpg)', text).group(2)    #拼接图片下载的url
            pic_mes = {'pic_url':pic_url,'chapter_name':chapter_name,'page':str(page)}              #生成图片信息的dict
            queue_pic.put(pic_mes,block=True,timeout=3)                                             #放入图片信息队列


#从图片信息队列中取出字典,根据信息生成下载目录进行下载图片
def parse_pic():
    global comic_name
    while not queue_pic.empty():
        pic_mes = queue_pic.get(block=True,timeout=3)

        pic_url = pic_mes['pic_url']
        chapter_name = pic_mes['chapter_name']
        page = pic_mes['page']
        pic = requests.get(pic_url)
        path = './%s/%s/第%s页.jpg'%(comic_name,chapter_name,page)    #拼接路径

        with open(path,'wb') as f:
            f.write(pic.content)
        print('已下载%s'%path)

if __name__  =='__main__':

    queue_chapter = queue.Queue()   #存放章节链接
    queue_pic = queue.Queue()       #存放图片信息（在哪个章节，是第几页，下载链接）

    start_url = input('comic index：')  #该漫画的首页
    Thread1 = []
    Thread2 = []
    for i in range(4):
        Thread1.append(threading.Thread(target=parse_chapter))      #四个线程处理章节
    for i in range(4):
        Thread2.append(threading.Thread(target=parse_pic))          #四个线程处理图片下载

    comic_name = parse_homepage(html_download(start_url))   #首先获取漫画名建立文件夹并获取所有章节链接放入队列
    if comic_name:
        time.sleep(1)
        for Thread in Thread1:
            Thread.start()
        time.sleep(1)
        for Thread in Thread2:
            Thread.start()

        for Thread in Thread1:
            Thread.join()
        for Thread in Thread2:
            Thread.join()

    end_time = datetime.datetime.now()
    print('爬取完毕，耗时',(end_time-start_time))



