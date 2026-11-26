import os
import psycopg2
from psycopg2.extras import Json
from pgvector import Vector
from pgvector.psycopg2 import register_vector


DATABASE_URL = os.getenv("DATABASE_URL")

TABLE_NAME = "municipal_document_chunks"
EMBEDDING_DIMENSION = 384


class PostgreSQLCollection:

    def _connect(self):
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL environment variable is not configured."
            )

        connection = psycopg2.connect(DATABASE_URL)
        register_vector(connection)
        return connection

    def init_db(self):
        connection = self._connect()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "CREATE EXTENSION IF NOT EXISTS vector;"
                )

                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                        id TEXT PRIMARY KEY,
                        document TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}',
                        embedding vector({EMBEDDING_DIMENSION}) NOT NULL
                    );
                    """
                )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def count(self):
        connection = self._connect()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT COUNT(*) FROM {TABLE_NAME};"
                )
                return cursor.fetchone()[0]

        finally:
            connection.close()

    def add(self, ids, documents, embeddings, metadatas):
        connection = self._connect()

        try:
            with connection.cursor() as cursor:
                for chunk_id, document, embedding, metadata in zip(
                    ids, documents, embeddings, metadatas
                ):
                    cursor.execute(
                        f"""
                        INSERT INTO {TABLE_NAME}
                            (id, document, metadata, embedding)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING;
                        """,
                        (
                            chunk_id,
                            document,
                            Json(metadata),
                            Vector(embedding)
                        )
                    )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def get(self, where=None, limit=None, include=None, ids=None):
        connection = self._connect()

        try:
            conditions = []
            parameters = []

            if where:
                conditions.append("metadata @> %s::jsonb")
                parameters.append(Json(where))

            if ids:
                conditions.append("id = ANY(%s)")
                parameters.append(ids)

            query = f"""
                SELECT id, document, metadata
                FROM {TABLE_NAME}
            """

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            if limit is not None:
                query += " LIMIT %s"
                parameters.append(limit)

            with connection.cursor() as cursor:
                cursor.execute(query, parameters)
                rows = cursor.fetchall()

            result = {
                "ids": [],
                "documents": [],
                "metadatas": []
            }

            include = include or ["metadatas"]

            for chunk_id, document, metadata in rows:
                result["ids"].append(chunk_id)

                if "documents" in include:
                    result["documents"].append(document)

                if "metadatas" in include:
                    result["metadatas"].append(metadata)

            return result

        finally:
            connection.close()

    def query(
        self,
        query_embeddings,
        n_results=5,
        include=None
    ):
        connection = self._connect()

        try:
            results = {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }

            include = include or [
                "documents",
                "metadatas",
                "distances"
            ]

            for query_embedding in query_embeddings:
                vector = Vector(query_embedding)

                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT
                            id,
                            document,
                            metadata,
                            embedding <-> %s AS distance
                        FROM {TABLE_NAME}
                        ORDER BY embedding <-> %s
                        LIMIT %s;
                        """,
                        (vector, vector, n_results)
                    )

                    rows = cursor.fetchall()

                for chunk_id, document, metadata, distance in rows:
                    results["ids"][0].append(chunk_id)

                    if "documents" in include:
                        results["documents"][0].append(document)

                    if "metadatas" in include:
                        results["metadatas"][0].append(metadata)

                    if "distances" in include:
                        results["distances"][0].append(float(distance) ** 2)

            return results

        finally:
            connection.close()

    def delete(self, ids):
        if not ids:
            return

        connection = self._connect()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {TABLE_NAME} WHERE id = ANY(%s);",
                    (ids,)
                )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()


collection = PostgreSQLCollection()


def init_vector_db():
    collection.init_db()