from flask import (
    Flask, 
    request, 
    jsonify, 
    send_file, 
    render_template, 
    send_from_directory
)
import image_processing
from redis import Redis
from rq import Queue
import sqlite3
import pickle
import glob
import os

app = Flask(__name__)
redis_conn = Redis(host='redis', port=6379)
queue = Queue(connection=redis_conn)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'files' not in request.files:
        return 'No file part'

    files = request.files.getlist('files')
    if not files:
        return 'No selected files'

    if not os.path.exists('temp'):
        os.makedirs('temp')

    job_ids = []
    multiplier = int(request.form['multiplier'])

    for file in files:
        image_path = os.path.join('temp', file.filename)
        file.save(image_path)

        job = queue.enqueue(image_processing.process_image, image_path, multiplier)
        job_ids.append(job.id)

    return jsonify({'job_ids': job_ids})

@app.route('/image_details')
def image_details():
    job_ids = request.args.getlist('job_ids')
    image_details_list = []

    for job_id in job_ids:
        job = queue.fetch_job(job_id)
        if job and job.get_status() == 'finished':
            resized_image_path, colors = job.result
            _, filename = os.path.split(job.args[0])
            original_image_path = filename
            resized_image_path = os.path.basename(resized_image_path)
            image_details_list.append({
                'original_image_path': original_image_path,
                'resized_image_path': resized_image_path,
                'colors': colors
            })
        else:
            return 'Error: Image not found or still being processed.'

    return render_template('image_details.html', image_details_list=image_details_list)

@app.route('/status/<job_id>')
def job_status(job_id):
    job = queue.fetch_job(job_id)
    if job:
        try:
            raw_data = job.data
            job_data = pickle.loads(raw_data)
        except pickle.UnpicklingError as e:
            return jsonify({'status': 'error', 'message': 'Deserialization error: ' + str(e)})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})

        if isinstance(job_data, tuple):
            job_data = tuple(item.decode('utf-8') if isinstance(item, bytes) else item for item in job_data)
        elif isinstance(job_data, bytes):
            job_data = job_data.decode('utf-8')

        return jsonify({'status': job.get_status(), 'data': job_data})
    else:
        return jsonify({'status': 'not found'})

@app.route('/download/<job_id>')
def download_resized_image(job_id):
    job = queue.fetch_job(job_id)
    if job and job.get_status() == 'finished':
        resized_image_path, _ = job.result  # O resultado é uma tupla (caminho da imagem redimensionada, cores)
        return send_file(resized_image_path, as_attachment=True)
    else:
        return 'Error: Image not found or still being processed.'

@app.route('/temp/<filename>')
def send_temp_file(filename):
    return send_from_directory('temp', filename)

@app.route('/download_temp/<filename>')
def download_temp_file(filename):
    return send_from_directory('temp', filename, as_attachment=True)

@app.route('/processed_images')
def processed_images():
    processed_jobs = []

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT original_image_path, resized_image_path, colors FROM images')
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        original_image_path, resized_image_path, colors = row
        processed_jobs.append({
            'original_image_path': os.path.basename(original_image_path),
            'resized_image_path': os.path.basename(resized_image_path),
            'colors': colors.split(',')
        })

    return render_template('processed_images.html', processed_jobs=processed_jobs)

if __name__ == '__main__':
    app.run(debug=True)