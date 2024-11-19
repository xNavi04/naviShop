from config import create_app
from routes import init_routes
#

app, login_manager, db = create_app()

init_routes(app, login_manager, db)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=4242)