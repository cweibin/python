from flask import Flask

app = Flask(__name__)

@app.route('/')
def company_intro():
    return '''
    <h1>Welcome to Our Company</h1>
    <p>We are a leading firm in our industry, committed to providing top-notch services and products to our clients.</p>
    '''

if __name__ == '__main__':
    app.run(debug=True)
