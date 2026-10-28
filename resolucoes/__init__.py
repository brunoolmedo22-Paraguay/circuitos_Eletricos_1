"""Módulo Exercícios Resolvidos — sistema colaborativo de resoluções acadêmicas.

Pacote dividido em:

* ``config``      — leitura de segredos e modo de operação;
* ``db``          — esquema relacional portátil (PostgreSQL / SQLite);
* ``storage``     — armazenamento persistente de PDFs (Supabase, banco ou disco);
* ``validators``  — validação de YouTube, Falstad e PDF;
* ``parecer``     — geração do parecer acadêmico em PDF;
* ``services``    — regras de negócio e permissões (sem Streamlit);
* ``ui``          — interface Streamlit do módulo.
"""
