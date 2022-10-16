FROM rappdw/docker-java-python

WORKDIR ./oir-tag_server
 
ADD . .

RUN python --version
RUN java -version
RUN pip install -r requirements.txt

CMD ["python", "main.py"]