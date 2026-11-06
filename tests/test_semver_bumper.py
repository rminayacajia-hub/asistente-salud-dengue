"""
Pruebas unitarias para el script de versionado SemVer.
Valida el cálculo de incrementos según Conventional Commits y formato oficial SemVer.
"""
import pytest
from scripts.semver_bumper import (
    validate_semver,
    determine_increment,
    calculate_next_release,
    calculate_next_snapshot,
    detect_manual_version_change,
    update_app_version_in_file,
)


def test_release_increment_and_calculation_main():
    """
    Verifica las reglas de incremento según Conventional Commits y el cálculo
    de versiones Release para la rama 'main', validando el cumplimiento estricto de SemVer.
    """
    base_version = "0.1.0"

    # 1. Caso MINOR: commit con prefijo feat:
    commits_minor = ["feat: implementa endpoint de triaje y orientación"]
    inc_minor = determine_increment(commits_minor)
    next_minor = calculate_next_release(base_version, inc_minor)
    assert inc_minor == "MINOR"
    assert next_minor == "0.2.0"
    assert validate_semver(next_minor) is True

    # 2. Caso PATCH: commit con prefijo fix:
    commits_patch = ["fix: corrige timeout en sondas de disponibilidad"]
    inc_patch = determine_increment(commits_patch)
    next_patch = calculate_next_release(base_version, inc_patch)
    assert inc_patch == "PATCH"
    assert next_patch == "0.1.1"
    assert validate_semver(next_patch) is True

    # 3. Caso PATCH para tareas de mantenimiento y documentación
    commits_chore_docs = [
        "chore: actualiza dependencias del backend",
        "docs: documenta especificación de arquitectura",
    ]
    inc_chore = determine_increment(commits_chore_docs)
    next_chore = calculate_next_release(base_version, inc_chore)
    assert inc_chore == "PATCH"
    assert next_chore == "0.1.1"
    assert validate_semver(next_chore) is True

    # 4. Caso MAJOR: commit con BREAKING CHANGE:
    commits_major_footer = [
        "fix: ajusta respuesta en endpoint de síntomas",
        "BREAKING CHANGE: se modifica la estructura del contrato JSON",
    ]
    inc_major_1 = determine_increment(commits_major_footer)
    next_major_1 = calculate_next_release(base_version, inc_major_1)
    assert inc_major_1 == "MAJOR"
    assert next_major_1 == "1.0.0"
    assert validate_semver(next_major_1) is True

    # 5. Caso MAJOR: commit con prefijo feat!: o fix!:
    commits_major_bang = ["feat!: elimina endpoint legacy de compatibilidad"]
    inc_major_2 = determine_increment(commits_major_bang)
    next_major_2 = calculate_next_release(base_version, inc_major_2)
    assert inc_major_2 == "MAJOR"
    assert next_major_2 == "1.0.0"
    assert validate_semver(next_major_2) is True

    # 6. Precedencia: Si hay feat y fix juntos, prevalece MINOR sobre PATCH
    commits_mixed = [
        "fix: soluciona detalle de logging",
        "feat: añade nueva herramienta de recuperación",
    ]
    inc_mixed = determine_increment(commits_mixed)
    next_mixed = calculate_next_release(base_version, inc_mixed)
    assert inc_mixed == "MINOR"
    assert next_mixed == "0.2.0"
    assert validate_semver(next_mixed) is True


def test_snapshot_rc_progression_develop():
    """
    Verifica la generación e incremento correlativo de versiones Snapshot para la
    rama 'develop' con nomenclatura X.Y.Z-SNAPSHOT-RC#, validando el cumplimiento
    estricto del patrón regex de SemVer.
    """
    base_version = "0.1.0"

    # 1. Sin tags previos de snapshot para la versión: inicia en RC1
    tags_vacios = []
    snapshot_1 = calculate_next_snapshot(base_version, tags_vacios)
    assert snapshot_1 == "0.1.0-SNAPSHOT-RC1"
    assert validate_semver(snapshot_1) is True

    # 2. Con un tag previo de snapshot RC1: incrementa a RC2
    tags_con_rc1 = ["v0.1.0-SNAPSHOT-RC1", "v0.0.9"]
    snapshot_2 = calculate_next_snapshot(base_version, tags_con_rc1)
    assert snapshot_2 == "0.1.0-SNAPSHOT-RC2"
    assert validate_semver(snapshot_2) is True

    # 3. Con múltiples tags: identifica el mayor correlativo (RC5 -> RC6)
    tags_multiples = [
        "v0.1.0-SNAPSHOT-RC1",
        "v0.1.0-SNAPSHOT-RC5",
        "v0.1.0-SNAPSHOT-RC2",
        "v0.1.0-SNAPSHOT-RC4",
    ]
    snapshot_6 = calculate_next_snapshot(base_version, tags_multiples)
    assert snapshot_6 == "0.1.0-SNAPSHOT-RC6"
    assert validate_semver(snapshot_6) is True


def test_manual_version_override_detection():
    """
    Verifica la detección y validación de modificaciones manuales de APP_VERSION
    en el diff del Pull Request.
    """
    # 1. Diff con asignación manual válida
    diff_valido = (
        "--- a/app/main.py\n"
        "+++ b/app/main.py\n"
        '@@ -10,1 +10,1 @@\n'
        '-APP_VERSION = "0.1.0"\n'
        '+APP_VERSION = "0.3.0"\n'
    )
    manual_ver = detect_manual_version_change(diff_valido)
    assert manual_ver == "0.3.0"
    assert validate_semver(manual_ver) is True

    # 2. Diff sin cambios en APP_VERSION
    diff_sin_version = (
        "--- a/app/main.py\n"
        "+++ b/app/main.py\n"
        '@@ -20,1 +20,1 @@\n'
        '-# comentario viejo\n'
        '+# comentario nuevo\n'
    )
    assert detect_manual_version_change(diff_sin_version) is None

    # 3. Diff con asignación manual INVÁLIDA según SemVer: debe lanzar ValueError
    diff_invalido = (
        "--- a/app/main.py\n"
        "+++ b/app/main.py\n"
        '@@ -10,1 +10,1 @@\n'
        '-APP_VERSION = "0.1.0"\n'
        '+APP_VERSION = "v1-invalida"\n'
    )
    with pytest.raises(ValueError, match="no cumple con el regex de SemVer"):
        detect_manual_version_change(diff_invalido)


def test_update_app_version_in_file(tmp_path):
    """
    Verifica la modificación segura y precisa de APP_VERSION en el archivo de destino.
    """
    test_file = tmp_path / "main.py"
    test_file.write_text(
        '"""Módulo main"""\n\nAPP_NAME = "asistente"\nAPP_VERSION = "0.1.0"\n\ndef test(): pass\n',
        encoding="utf-8",
    )

    update_app_version_in_file(test_file, "0.2.0")
    nuevo_contenido = test_file.read_text(encoding="utf-8")
    assert 'APP_VERSION = "0.2.0"' in nuevo_contenido
    assert 'APP_NAME = "asistente"' in nuevo_contenido

    # Si se intenta asignar una versión inválida, debe lanzar ValueError sin modificar el archivo
    with pytest.raises(ValueError, match="Versión inválida"):
        update_app_version_in_file(test_file, "version_mala")
