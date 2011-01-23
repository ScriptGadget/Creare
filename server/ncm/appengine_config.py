from gaesessions import SessionMiddleware
def webapp_add_wsgi_middleware(app):
    app = SessionMiddleware(app, cookie_key='xT9SEPmacUU+ZgfVu+Zpwn8mB+aXwqBFDe/Y52+N3Xj4+dH9STsVH+DhGQgLtCs/7zq0Jbkkq36oJcBYsMM2cw==')
    return app
