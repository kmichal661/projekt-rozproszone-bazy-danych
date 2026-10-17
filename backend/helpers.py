from starlette.responses import HTMLResponse


def graphiql(request):
    """Zwraca interfejs GraphiQL dla endpointu /graphql."""
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="pl">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Sklep rozproszony - GraphQL</title>
            <link rel="stylesheet"
                  href="https://unpkg.com/graphiql@1.4.7/graphiql.min.css" />
          </head>
          <body style="margin: 0">
            <div id="graphiql" style="height: 100vh"></div>

            <script src="https://unpkg.com/react@17/umd/react.production.min.js"></script>
            <script src="https://unpkg.com/react-dom@17/umd/react-dom.production.min.js"></script>
            <script src="https://unpkg.com/graphiql@1.4.7/graphiql.min.js"></script>

            <script>
              const fetcher = (params) =>
                fetch(window.location.pathname, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(params),
                }).then((response) => response.json());

              ReactDOM.render(
                React.createElement(GraphiQL, { fetcher }),
                document.getElementById("graphiql")
              );
            </script>
          </body>
        </html>
        """
    )
