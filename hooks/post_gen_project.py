import os
import sys
import shutil

_use_celery = '{{cookiecutter._use_celery}}'


if _use_celery == "no":
    base_path = os.getcwd()
    app_path = os.path.join(
        base_path,
        '{{cookiecutter.app_name}}',
    )
    tasks_path = os.path.join(app_path, 'tasks')
    celery_app_path = os.path.join(app_path, 'celery_app.py')

    try:
        shutil.rmtree(tasks_path)
    except Exception:
        print("ERROR: cannot delete celery tasks path %s" % tasks_path)
        sys.exit(1)

    try:
        os.remove(celery_app_path)
    except Exception:
        print("ERROR: cannot delete celery application file")
        sys.exit(1)

    try:
        os.remove(os.path.join(base_path, "tests", "test_celery.py"))
    except Exception:
        print("ERROR: cannot delete celery tests files")
        sys.exit(1)
