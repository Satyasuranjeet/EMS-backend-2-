from flask import Flask, request, jsonify, render_template, redirect
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from bson.objectid import ObjectId
from flask_restful import Api, Resource
import json
from flask_cors import CORS  # Import CORS

# Initialize the Flask application
app = Flask(__name__)

# Enable CORS for all routes and origins (allowing React frontend on localhost:3000)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

# MongoDB URI
app.config["MONGO_URI"] = "mongodb+srv://satya:satya@cluster0.8thgg4a.mongodb.net/employee_management?retryWrites=true&w=majority"
app.config['SECRET_KEY'] = 'df78gs9hwv893hcwhc9h3c98hwc329hw30h40'

mongo = PyMongo(app)
login_manager = LoginManager()
login_manager.init_app(app)
api = Api(app)

# Admin Model for login
class Admin(UserMixin):
    def __init__(self, username, password):
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    admin = mongo.db.admin.find_one({"_id": ObjectId(user_id)})
    if admin:
        return Admin(admin['username'], admin['password'])
    return None

# Routes for Admin Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = mongo.db.admin.find_one({"username": username})
        if admin and admin['password'] == password:
            login_user(Admin(admin['username'], admin['password']))
            return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# CRUD Operations for Employee
@app.route('/employee', methods=['POST'])
def add_employee():
    data = request.get_json()
    if not all(key in data for key in ('first_name', 'last_name', 'email', 'salary', 'department_id', 'role_id')):
        return jsonify({'message': 'Missing required fields'}), 400
    
    mongo.db.employee.insert_one({
        'first_name': data['first_name'],
        'last_name': data['last_name'],
        'email': data['email'],
        'salary': data['salary'],
        'department_id': data['department_id'],
        'role_id': data['role_id']
    })
    return jsonify({'message': 'Employee added successfully'}), 201

@app.route('/employees', methods=['GET'])
def get_employees():
    try:
        employees = mongo.db.employee.find()
        result = []
        for e in employees:
            result.append({
                'id': str(e['_id']),
                'first_name': e['first_name'],
                'last_name': e['last_name'],
                'email': e['email'],
                'salary': e['salary'],
                'department': e['department_id'],
                'role': e['role_id']
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"message": f"Error fetching employees: {str(e)}"}), 500

@app.route('/employee/<id>', methods=['PUT'])
def update_employee(id):
    data = request.get_json()
    mongo.db.employee.update_one({'_id': ObjectId(id)}, {
        '$set': {
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'email': data['email'],
            'salary': data['salary'],
            'department_id': data['department_id'],
            'role_id': data['role_id']
        }
    })
    return jsonify({'message': 'Employee updated successfully'})

@app.route('/employee/<id>', methods=['DELETE'])
def delete_employee(id):
    mongo.db.employee.delete_one({'_id': ObjectId(id)})
    return jsonify({'message': 'Employee deleted successfully'})

# External REST API for Employee Data
class EmployeeAPI(Resource):
    def get(self, employee_id):
        employee = mongo.db.employee.find_one({"_id": ObjectId(employee_id)})
        if employee:
            return {
                'id': str(employee['_id']),
                'first_name': employee['first_name'],
                'last_name': employee['last_name'],
                'email': employee['email'],
                'salary': employee['salary']
            }
        return {'message': 'Employee not found'}, 404

api.add_resource(EmployeeAPI, '/api/employee/<string:employee_id>')

# Automated Reporting (Employee Statistics)
@app.route('/report', methods=['GET'])
def generate_report():
    total_employees = mongo.db.employee.count_documents({})
    total_salary = mongo.db.employee.aggregate([{
        '$group': {'_id': None, 'total_salary': {'$sum': '$salary'}}
    }])
    total_salary = list(total_salary)[0]['total_salary']
    
    report = {
        'total_employees': total_employees,
        'total_salary': total_salary
    }
    return jsonify(report)
# Add these routes to your existing Flask application

@app.route('/dashboard/report', methods=['GET'])
def dashboard_report():
    total_employees = mongo.db.employee.count_documents({})
    total_salary = mongo.db.employee.aggregate([{
        '$group': {'_id': None, 'total_salary': {'$sum': '$salary'}}
    }])
    total_salary = list(total_salary)[0]['total_salary']

    # Aggregate salary by department
    department_stats = list(mongo.db.employee.aggregate([
        {
            '$group': {
                '_id': '$department_id',
                'total_salary': {'$sum': '$salary'},
                'avg_salary': {'$avg': '$salary'},
                'employee_count': {'$sum': 1}
            }
        },
        {
            '$project': {
                'department': '$_id',
                'total_salary': 1,
                'avg_salary': 1,
                'employee_count': 1
            }
        }
    ]))

    # Find department with most employees and highest total salary
    department_with_most_employees = max(department_stats, key=lambda x: x['employee_count'])['department']
    highest_paid_department = max(department_stats, key=lambda x: x['total_salary'])['department']

    report = {
        'total_employees': total_employees,
        'total_salary': total_salary,
        'avg_salary': total_salary / total_employees,
        'department_stats': department_stats,
        'highest_paid_department': highest_paid_department,
        'department_with_most_employees': department_with_most_employees,
        'salary_growth_rate': 5.5  # Example static value, replace with actual calculation
    }
    return jsonify(report)

if __name__ == '__main__':
    app.run(debug=True)
