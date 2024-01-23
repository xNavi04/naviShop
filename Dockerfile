FROM python:3-alpine3.15
WORKDIR /app
COPY . /app

ENV SECRET_KEY=asdf89sdahvfad0vuhnadjiwsbjwe
ENV STRIPE_API_KEY=sk_test_51OW4uJJumIMB2fjpZXQff4pMYNmfjMlYsnZ5looS8q5ogLMVJnFywmQk85DvyJE2ijvxQLbugUMtyvb3XfYBsTZU00qek4QV4P
ENV ENDPOINT_SECRET=whsec_NznMPvwr6xaY22MihnOnOrK8x9oChQ0L
ENV SQLALCHEMY_DATABASE_URI=postgresql://iiphaxav:AYNmmWP0WyoXW1drfchXtK5gNSDlrZjV@manny.db.elephantsql.com/iiphaxav


RUN pip install -r requirements.txt
EXPOSE 3000
CMD python ./main.py