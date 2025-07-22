建立文档库
```
cd backend
mkdir data
cd data
mkdir pdf
```
在pdf下存储产品文档
```
cd ../..
```

下载依赖
```
pip install fastapi uvicorn -i https://pypi.tuna.tsinghua.edu.cn/simple
```
根据报错 缺哪个依赖以此类推进行下载

```
pip install fastapi==0.115.9
```

建立向量数据库
```
python seed_db.py
```

启动后端
```
uvicorn main:ICS --reload
```
而后直接访问

```
http://127.0.0.1:8000/chat
```

如需修改端口号等
```
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```