#!/usr/bin/env python3
"""Run as root after installing Ubuntu's postgresql package and lumen OS user.
Creates local peer-authenticated databases, without password handling.
Does not change the application's active database or migrate data.
"""
import subprocess

def sql(query):
    return subprocess.check_output(['runuser','-u','postgres','--','psql','-X','-At','-v','ON_ERROR_STOP=1','-c',query],text=True).strip()

if sql("SELECT count(*) FROM pg_roles WHERE rolname='lumen'")=='0':
    sql('CREATE ROLE lumen LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE')
for name in ('lumen','lumen_qa'):
    if sql(f"SELECT count(*) FROM pg_database WHERE datname='{name}'")=='0':
        sql(f'CREATE DATABASE {name} OWNER lumen')
    sql(f'REVOKE ALL ON DATABASE {name} FROM PUBLIC')
print('Local Lumen PostgreSQL databases ready. Application not switched.')
