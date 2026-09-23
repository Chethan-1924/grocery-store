import os
from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",  # change this before deploying publicly
        DATABASE=os.path.join(app.instance_path, "grocery.sqlite"),
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    import db
    db.init_app(app)

    import auth
    app.register_blueprint(auth.bp)

    import main
    app.register_blueprint(main.bp)

    import api
    app.register_blueprint(api.bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
