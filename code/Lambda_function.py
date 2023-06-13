import boto3
import csv
import re

def preprocess_csv(rows):
    # 중복 제거
    rows = [row for i, row in enumerate(rows) if row not in rows[:i]]

    # NULL 값 처리
    rows = [[value if value else '' for value in row] for row in rows]

    # 특수 문자 제거
    rows = [[re.sub(r'[^\w\s]', '', str(value)) for value in row] for row in rows]

    return rows

def preprocess_column_names(column_names):
    # 컬럼 이름 전처리 함수
    column_names = [re.sub(r'[^\w\s]', '', str(name)) for name in column_names]
    return column_names

def revert_column_names(rows, original_column_names):
    # 컬럼 이름을 변경하기 전으로 되돌리는 함수
    rows[0] = original_column_names
    return rows

def lambda_handler(event, context):
    # S3 버킷 정보
    source_bucket = event['Records'][0]['s3']['bucket']['name']
    source_key = event['Records'][0]['s3']['object']['key']
    
    # S3 클라이언트 생성
    s3 = boto3.client('s3')
    
    try:
        # CSV 파일 다운로드
        response = s3.get_object(Bucket=source_bucket, Key=source_key)
        data = response['Body'].read().decode('utf-8')
        
        # 전처리 작업 수행
        rows = list(csv.reader(data.splitlines()))
        original_column_names = rows[0]  # 원래의 컬럼 이름 저장
        
        # 컬럼 이름 전처리
        original_column_names = preprocess_column_names(original_column_names)
        rows = [original_column_names] + rows[1:]  # 컬럼 이름 변경
        
        # 전처리 작업 단계별로 분할
        total_steps = 3
        step_size = len(rows) // total_steps
        
        preprocessed_rows = []
        for i in range(total_steps):
            start = i * step_size
            end = (i + 1) * step_size
            step_rows = rows[start:end]
            preprocessed_step_rows = preprocess_csv(step_rows)
            preprocessed_rows += preprocessed_step_rows
            
            # 클라이언트로 진행 상황 업데이트 전송
            progress = int(((i + 1) / total_steps) * 100)
        
        # 전처리된 데이터를 원래의 컬럼 이름으로 되돌림
        preprocessed_rows = revert_column_names(preprocessed_rows, original_column_names)
        
        # 전처리된 데이터를 CSV 형식으로 변환
        preprocessed_data = '\n'.join([','.join(row) for row in preprocessed_rows])
        
        # 전처리된 데이터를 다시 S3에 저장
        target_bucket = 'updatecsv4'  # 전처리된 데이터를 저장할 대상 S3 버킷
        target_key = 'preprocessed/' + source_key  # 전처리된 데이터의 저장 경로
        s3.put_object(Body=preprocessed_data, Bucket=target_bucket, Key=target_key, ContentType='text/csv')

        return {
            'statusCode': 200,
            'body': '전처리 및 저장 완료'
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': '에러 발생: {}'.format(str(e))
        }