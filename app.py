from flask import Flask,jsonify,request,render_template
from flask_cors import CORS
import pandas as pd
from io import BytesIO
import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client=Groq(api_key=os.getenv('GROQ_API_KEY'))

app=Flask(__name__)
CORS(app)

@app.route('/',methods=['GET'])
def home():
    return "Excel Extractor API is running"

@app.route('/extract',methods=['POST'])
def extract():
    file=request.files.get('file')

    if not file or file.filename=="":
        return jsonify('No file uploaded'),400

    if not file.filename.lower().endswith(('.xlsx','.xls')):
        return jsonify('Please upload a valid Excel file'),400

    try:
        df=pd.read_excel(BytesIO(file.read()))
        df=df.astype(object).where(pd.notna(df),None)

        records=df.to_dict(orient='records')

        return jsonify(
            success=True,
            columns=df.columns.tolist(),
            rows=len(df),
            data=records
        )
    except Exception:
        app.logger.exception('Error processing the Excel file')
        return jsonify('Error processing the Excel file'),500

@app.route('/analyze',methods=['POST'])
def analyze():
    print('Analyze endpoint called')
    data=request.get_json().get('data',[])
    question=request.get_json().get('question','').strip()

    if not data or not question:
        return jsonify('Data and question are required'),400

    try:

        response=client.chat.completions.create(
            model="openai/gpt-oss-20b",
            
            messages=[
                {
                    'role': 'system',
                    'content': """
You are an Excel data analyst.
Analyze the supplied Excel data according to the user's question.

Return ONLY valid JSON in this format:
{
  "summary": "Brief analysis summary",
  "columns": ["ID", "Name", "Observation"],
  "data": [
    {
      "ID": 1,
      "Name": "Aarav",
      "Observation": "Example observation"
    }
  ]
}

Rules:
- The columns must match the keys in each data object.
- Include relevant analyzed values and observations.
- Do not use Markdown or code fences.
- Do not invent facts that are not supported by the data.
- If the user requests a summary, statistics, or comparison,
  structure the useful results as table rows.
"""
                },
                {
                    'role':'user',
                    'content':(f'Analyze the excel data{json.dumps(data,default=str)}\n\n'
                     f'Question: {question}')
                }
            ],
            max_tokens=500,
            temperature=0.2
        )
        answer=response.choices[0].message.content

        result=json.loads(answer)

        return jsonify(
            status=True,
            summary=result.get('summary',''),
            columns=result.get('columns',[]),   
            data=result.get('data',[])
        )
    except Exception:
        app.logger.exception('Error analyzing the data')
        return jsonify('Error analyzing the data'), 500

if(__name__)==('__main__'):
    app.run(debug=True,port=5000)