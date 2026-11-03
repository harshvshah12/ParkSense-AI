import httpx, pathlib, time

f = pathlib.Path('tmp/test.jpg')
print('uploading', f.exists())
with httpx.Client(timeout=120) as c:
    r = c.post('http://127.0.0.1:8000/upload', files={'file': ('test.jpg', f.read_bytes(), 'image/jpeg')})
    print('upload', r.status_code, r.text)
    jobid = r.json().get('job_id')
    print('job', jobid)
    for i in range(60):
        time.sleep(1)
        r2 = c.get(f'http://127.0.0.1:8000/analyze/{jobid}')
        j = r2.json()
        print(i+1, j['status'], j.get('progress'), j.get('occupancy_ratio'), j.get('empty_spaces'))
        if j['status'] in ('completed', 'failed'):
            print('final', j)
            break
