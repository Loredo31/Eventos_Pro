from flask_pymongo import PyMongo
import bcrypt
from datetime import datetime

class UserModel:
    def __init__(self, mongo):
        self.mongo = mongo
        self.collection = mongo.db.users
    
    def create_user(self, nombre, email, password, rol='cliente'):
        """Crear un nuevo usuario"""
        # Verificar si el email ya existe
        if self.collection.find_one({'email': email}):
            return None
        
        # Hash de la contraseña
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        user = {
            'nombre': nombre,
            'email': email,
            'password': hashed_password,
            'rol': rol,
            'fecha_registro': datetime.utcnow(),
            'activo': True
        }
        
        result = self.collection.insert_one(user)
        return str(result.inserted_id)
    
    def find_by_email(self, email):
        """Buscar usuario por email"""
        return self.collection.find_one({'email': email})
    
    def find_by_id(self, user_id):
        """Buscar usuario por ID"""
        from bson import ObjectId
        try:
            return self.collection.find_one({'_id': ObjectId(user_id)})
        except:
            return None
    
    def verify_password(self, user, password):
        """Verificar contraseña"""
        return bcrypt.checkpw(password.encode('utf-8'), user['password'])
    
    def update_rol(self, user_id, nuevo_rol):
        """Actualizar rol de usuario"""
        from bson import ObjectId
        self.collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'rol': nuevo_rol}}
        )