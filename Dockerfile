FROM odoo:17.0

USER root

COPY ./requirements.txt /mnt/extra-addons/requirements.txt
COPY ./requirements-dev.txt /mnt/extra-addons/requirements-dev.txt
WORKDIR /mnt/extra-addons

RUN pip install passlib
RUN pip install -r requirements.txt
RUN pip install -r requirements-dev.txt

COPY ./entrypoint.sh /
RUN ls -la /
USER odoo

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]