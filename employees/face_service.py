import os

import cv2
import numpy as np
from django.conf import settings
from django.core.files.base import ContentFile

from .models import Employee

FACE_MODEL_DIR = os.path.join(settings.MEDIA_ROOT, 'face_models')
LBPH_MODEL_PATH = os.path.join(FACE_MODEL_DIR, 'lbph_model.yml')
CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
_face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
_lbph_recognizer = None
_lbph_model_mtime = None


def _ensure_face_detector():
    if _face_cascade.empty():
        raise RuntimeError(
            'OpenCV Haar cascade is missing. Reinstall opencv-contrib-python.'
        )


def _detect_face_gray(rgb_image, size=(200, 200)):
    _ensure_face_detector()
    gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
    faces = _face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
    )
    if len(faces) == 0:
        return None
    x, y, width, height = max(faces, key=lambda face: face[2] * face[3])
    return cv2.resize(gray[y:y + height, x:x + width], size)


def _detect_face_gray_from_path(path):
    if not path or not os.path.isfile(path):
        return None
    image = cv2.imread(path)
    if image is None:
        return None
    return _detect_face_gray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def _dlib_identify(rgb_image, employees):
    try:
        import face_recognition
    except ImportError as error:
        raise RuntimeError('face_recognition is not installed.') from error

    locations = face_recognition.face_locations(rgb_image)
    encodings = face_recognition.face_encodings(rgb_image, locations)
    if not encodings:
        return None, None

    best_match, best_distance = None, 0.5
    for employee in employees:
        if not employee.face_encoding:
            continue
        known = np.frombuffer(employee.face_encoding, dtype=np.float64)
        distance = np.linalg.norm(known - encodings[0])
        if distance < best_distance:
            best_match, best_distance = employee, distance
    return best_match, best_distance


def _lbph_identify(rgb_image):
    global _lbph_recognizer, _lbph_model_mtime
    if not os.path.exists(LBPH_MODEL_PATH):
        return None, None
    face = _detect_face_gray(rgb_image)
    if face is None:
        return None, None
    model_mtime = os.path.getmtime(LBPH_MODEL_PATH)
    if _lbph_recognizer is None or _lbph_model_mtime != model_mtime:
        _lbph_recognizer = cv2.face.LBPHFaceRecognizer_create()
        _lbph_recognizer.read(LBPH_MODEL_PATH)
        _lbph_model_mtime = model_mtime
    label, confidence = _lbph_recognizer.predict(face)
    if confidence > 70:
        return None, confidence
    try:
        return Employee.objects.get(pk=label), confidence
    except Employee.DoesNotExist:
        return None, confidence


def identify(rgb_image):
    if settings.USE_DLIB:
        employees = Employee.objects.exclude(face_encoding__isnull=True)
        return _dlib_identify(rgb_image, employees)
    if not hasattr(cv2, 'face'):
        raise RuntimeError('Install opencv-contrib-python for LBPH face recognition.')
    return _lbph_identify(rgb_image)


def register_employee_face(employee):
    if not employee.photo:
        return False

    if settings.USE_DLIB:
        try:
            import face_recognition
        except ImportError as error:
            raise RuntimeError('face_recognition is not installed.') from error
        image = face_recognition.load_image_file(employee.photo.path)
        encodings = face_recognition.face_encodings(image)
        if not encodings:
            return False
        employee.face_encoding = np.asarray(encodings[0], dtype=np.float64).tobytes()
        employee.save(update_fields=['face_encoding'])
        return True

    return _detect_face_gray_from_path(employee.photo.path) is not None


def register_live_face(employee, rgb_image):
    return register_live_faces(employee, [rgb_image])


def register_live_faces(employee, rgb_images):
    if len(rgb_images) < 3:
        return False

    if settings.USE_DLIB:
        try:
            import face_recognition
        except ImportError as error:
            raise RuntimeError('face_recognition is not installed.') from error
        encodings = []
        for rgb_image in rgb_images:
            detected = face_recognition.face_encodings(
                rgb_image, face_recognition.face_locations(rgb_image)
            )
            if not detected:
                return False
            encodings.append(detected[0])
        if not encodings:
            return False
        employee.face_encoding = np.mean(encodings, axis=0).astype(np.float64).tobytes()
        employee.save(update_fields=['face_encoding'])
        return True

    for rgb_image in rgb_images:
        if _detect_face_gray(rgb_image) is None:
            return False
    rgb_image = rgb_images[-1]
    success, encoded = cv2.imencode('.jpg', cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR))
    if not success:
        return False
    employee.photo.save(f'employee_{employee.pk}.jpg', ContentFile(encoded.tobytes()), save=True)
    return train_lbph() > 0


def train_lbph():
    if not hasattr(cv2, 'face'):
        raise RuntimeError('Install opencv-contrib-python for LBPH face recognition.')
    faces, labels = [], []
    for employee in Employee.objects.filter(photo__isnull=False).exclude(photo=''):
        if not employee.photo:
            continue
        face = _detect_face_gray_from_path(employee.photo.path)
        if face is not None:
            faces.append(face)
            labels.append(employee.pk)
    if not faces:
        return 0
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.asarray(labels))
    os.makedirs(FACE_MODEL_DIR, exist_ok=True)
    recognizer.write(LBPH_MODEL_PATH)
    return len(faces)
