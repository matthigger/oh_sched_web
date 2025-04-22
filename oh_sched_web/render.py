# this script is run to deploy app on render

if __name__ == '__main__':
    import os

    from oh_sched_web.app import app

    app.run(host='0.0.0.0',
            port=os.environ.get('PORT'))
