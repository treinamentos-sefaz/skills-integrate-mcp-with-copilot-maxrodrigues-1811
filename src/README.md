# API de Atividades da Mergington High School

Uma aplicação FastAPI super simples que permite aos estudantes visualizar e se inscrever em atividades extracurriculares.

## Funcionalidades

- Visualizar todas as atividades extracurriculares disponíveis
- Buscar atividades por nome, categoria, descrição ou horário
- Filtrar atividades por categoria e ordenar por nome ou horário
- Visualizar participantes inscritos
- Professores autenticados podem inscrever ou remover estudantes

## Acesso de professores

As credenciais ficam em `src/teachers.json`, que não deve ser enviado ao Git.
Para criar uma conta de professor, execute na raiz do repositório:

```sh
python src/create_teacher.py
```

O script solicita o nome de usuário e a senha sem exibi-la, e grava somente um
hash PBKDF2 com salt. Os alunos podem consultar atividades e participantes sem
entrar; somente professores autenticados podem alterar inscrições.

As sessões duram oito horas e usam um cookie `HttpOnly` com `SameSite=Lax`.
Ao publicar por HTTPS, defina `COOKIE_SECURE=true`; mantenha o valor padrão
(`false`) apenas para desenvolvimento local em HTTP.

## Primeiros Passos

1. Instale as dependências:

   ```
   pip install -r requirements.txt
   ```

2. Execute a aplicação:

   ```
   uvicorn src.app:app --reload
   ```

3. Abra seu navegador e vá para:
   - Documentação da API: http://localhost:8000/docs
   - Documentação alternativa: http://localhost:8000/redoc

## Endpoints da API

| Método | Endpoint                                                          | Descrição                                                           |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Obter todas as atividades com seus detalhes e contagem atual de participantes |
| POST   | `/auth/login`                                                      | Entrar como professor                                               |
| GET    | `/auth/me`                                                         | Consultar a sessão atual                                            |
| POST   | `/auth/logout`                                                     | Encerrar a sessão atual                                             |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Professor: inscrever um estudante                                   |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Professor: remover um estudante de uma atividade                  |

## Modelo de Dados

A aplicação usa um modelo de dados simples com identificadores significativos:

1. **Atividades** - Usa o nome da atividade como identificador:

   - Descrição
   - Cronograma
   - Categoria
   - Ordem do horário (minutos desde o início da segunda-feira), para classificação cronológica
   - Número máximo de participantes permitidos
   - Lista de emails de estudantes que estão inscritos

2. **Estudantes** - Usa email como identificador:
   - Nome
   - Nível da série

Todos os dados são armazenados na memória, o que significa que os dados serão resetados quando o servidor reiniciar.
