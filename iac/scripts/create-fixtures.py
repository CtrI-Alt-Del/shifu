from __future__ import annotations

import csv
import json
from pathlib import Path


FIXTURE_DIRECTORY = Path(__file__).resolve().parents[1] / "fixtures"


def _pdf_bytes(text: str) -> bytes:
    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT\n/F1 18 Tf\n72 760 Td\n({escaped_text}) Tj\nET\n".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{object_number} 0 obj\n".encode("ascii"))
        document.extend(body)
        document.extend(b"\nendobj\n")

    xref_offset = len(document)
    document.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(document)


def create_fixtures() -> None:
    public_directory = FIXTURE_DIRECTORY / "public"
    private_directory = FIXTURE_DIRECTORY / "private"
    archive_directory = FIXTURE_DIRECTORY / "archive"
    for directory in (public_directory, private_directory, archive_directory):
        directory.mkdir(parents=True, exist_ok=True)

    (public_directory / "exemplo.txt").write_text(
        "Arquivo publico de demonstracao da Atividade 3 - Shifu.\n",
        encoding="utf-8",
    )
    (private_directory / "exemplo.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="180" viewBox="0 0 480 180">'
        '<rect width="480" height="180" fill="#eef2ff"/>'
        '<text x="24" y="95" font-family="sans-serif" font-size="24" fill="#312e81">Shifu - arquivo privado de teste</text>'
        "</svg>\n",
        encoding="utf-8",
    )
    (private_directory / "exemplo.json").write_text(
        json.dumps(
            {
                "project": "Shifu",
                "purpose": "atividade-academica",
                "synthetic": True,
                "created_by": "create-fixtures.py",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    with (private_directory / "exemplo.csv").open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["learner_id", "event_type", "score"])
        writer.writerows(
            [
                ["learner-001", "activity_submitted", 88],
                ["learner-002", "activity_submitted", 74.5],
                ["learner-003", "diagnostic_completed", 92],
            ]
        )
    (private_directory / "exemplo.txt").write_text(
        "Conteudo ficticio e privado para demonstracao do bucket S3.\n",
        encoding="utf-8",
    )
    (private_directory / "documento-v1.pdf").write_bytes(
        _pdf_bytes("Shifu storage lab - versao 1 do PDF")
    )
    (private_directory / "documento-v2.pdf").write_bytes(
        _pdf_bytes("Shifu storage lab - versao 2 do mesmo PDF")
    )

    with (archive_directory / "historico.csv").open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["event_id", "learner_id", "event_type", "occurred_at"])
        for event_number in range(1, 7001):
            learner_number = ((event_number - 1) % 10) + 1
            writer.writerow(
                [
                    f"archive-event-{event_number:05d}",
                    f"learner-{learner_number:03d}",
                    "activity_submitted" if event_number % 2 else "material_viewed",
                    f"2026-09-{((event_number - 1) % 28) + 1:02d}T12:00:00Z",
                ]
            )

    print(f"Fixtures criadas em: {FIXTURE_DIRECTORY}")
    print("O CSV de arquivo foi gerado com tamanho suficiente para demonstrar a transicao S3 para STANDARD_IA.")


if __name__ == "__main__":
    create_fixtures()
