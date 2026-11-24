import os
import sys
from pathlib import Path

from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow,
                               QMessageBox)

import src.services as Services
from src.output import Ui_MainWindow
from src.services import READERS

os.environ.pop("QT_QPA_PLATFORMTHEME", None)   # не даём Qt подхватить GTK-тему GNOME
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")  # форсируем X11 вместо Wayland


def main(file_path: str, output_path=None, *, reader_options=None, mapping=None,
         constants=None, primary='Depth [m]', measurements=None):
    """Read supported source. If output_path is provided, validate/export ODV TXT.
    Without output_path return DataFrame (no implicit output.txt overwrite).
    """
    source = Path(file_path)
    if not source.exists():
        raise FileNotFoundError(source)
    reader = READERS.get(source.suffix.lower())
    if reader is None:
        raise ValueError(f'Unknown extension {source.suffix}')
    frame = reader(source, **(reader_options or {}))
    if output_path is None:
        return frame
    return Services.write_odv(frame, output_path, mapping, constants, primary, measurements)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.btnOpen.clicked.connect(self.open_file_dialog)


    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите входной файл",
            "",
            "Все файлы (*);;Текстовые файлы (*.txt);;CSV файлы (*.csv)"
        )
        if not file_path:
            return

        # 2. Выбираем, куда сохранить результат
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Куда сохранить результат",
            "output.txt",
            "ODV TXT (*.txt);;Все файлы (*)"
        )
        if not output_path:
            return

        reader_options = {}                 # доп. опции для конкретного ридера
                # Маппинг: реальное имя колонки -> ODV-имя с единицами
        mapping = {
            "depth": "depth [m]",
            "temperature": "temperature [ITS-90, deg C]",
            "salinity": "salinity [PSU]",
        }

        # Метаданные: в файле есть cruise и station, поэтому задаём только то,
        # чего нет. Убрал Cruise/Station — иначе продублируются.
        constants = {
            "Type": "B",      # B = bottle data
            "Monitor": "1",
        }

        primary = "depth [m]"   # тоже переименованное имя!

        # Ключи measurements = ODV-имена ПОСЛЕ маппинга, с единицами в заголовке
        measurements = {
            "temperature [ITS-90, deg C]": "ITS-90, deg C",
            "salinity [PSU]": "PSU",
        }

        try:
            frame = main(file_path)          # без output_path — просто чтение
            print("Колонки файла:", list(frame.columns))
            QMessageBox.information(self, "Колонки", "\n".join(frame.columns))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать файл: {e}")
            return


        try:
            main(
                file_path,
                output_path,
                reader_options=reader_options,
                mapping=mapping,
                constants=constants,
                primary=primary,
                measurements=measurements
            )
            self.ui.statusLabel.setText(f"Обработка {Path(file_path).name}…")
            QApplication.processEvents()

            self.ui.statusLabel.setText(f"Готово: {Path(output_path).name}")

        except FileNotFoundError as e:
            QMessageBox.critical(self, "Ошибка", f"Файл не найден: {e}")
        except ValueError as e:
            QMessageBox.critical(self, "Ошибка", f"Неподдерживаемый формат: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обработать файл:\n{e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
