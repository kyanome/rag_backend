"""プロンプトテンプレートの値オブジェクト。

変数補間機能を持つプロンプトテンプレートを定義する。
"""

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PromptVariable(BaseModel):
    """プロンプト変数を表す値オブジェクト。

    Attributes:
        name: 変数名
        description: 変数の説明
        required: 必須かどうか
        default: デフォルト値
    """

    name: str = Field(..., description="変数名")
    description: str | None = Field(None, description="変数の説明")
    required: bool = Field(True, description="必須かどうか")
    default: Any | None = Field(None, description="デフォルト値")

    model_config = {"frozen": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """変数名のバリデーション。"""
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError(
                f"Invalid variable name: {v}. "
                "Must start with letter or underscore and contain only alphanumeric characters."
            )
        return v


class PromptTemplate(BaseModel):
    """プロンプトテンプレートを表す値オブジェクト。

    Attributes:
        name: テンプレート名
        template: テンプレート文字列
        variables: 変数定義のリスト
        description: テンプレートの説明
        version: バージョン
        metadata: その他のメタデータ
    """

    name: str = Field(..., description="テンプレート名")
    template: str = Field(..., description="テンプレート文字列")
    variables: list[PromptVariable] = Field(
        default_factory=list, description="変数定義のリスト"
    )
    description: str | None = Field(None, description="テンプレートの説明")
    version: str = Field("1.0.0", description="バージョン")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="その他のメタデータ"
    )

    model_config = {"frozen": True}

    @field_validator("template")
    @classmethod
    def validate_template(cls, v: str) -> str:
        """テンプレートのバリデーション。"""
        if not v or not v.strip():
            raise ValueError("Template cannot be empty")
        return v

    def extract_variables(self) -> set[str]:
        """テンプレートから変数名を抽出する。

        Returns:
            変数名のセット
        """
        # {variable_name} 形式の変数を抽出
        pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"
        return set(re.findall(pattern, self.template))

    def validate_variables(self) -> None:
        """変数定義の整合性を検証する。

        Raises:
            ValueError: 変数定義に不整合がある場合
        """
        template_vars = self.extract_variables()
        defined_vars = {var.name for var in self.variables}

        # テンプレートにあって定義にない変数
        undefined_vars = template_vars - defined_vars
        if undefined_vars:
            raise ValueError(f"Variables in template but not defined: {undefined_vars}")

        # 定義にあってテンプレートにない変数（警告のみ）
        unused_vars = defined_vars - template_vars
        if unused_vars:
            import warnings

            warnings.warn(
                f"Variables defined but not used in template: {unused_vars}",
                UserWarning,
                stacklevel=2,
            )

    def format(self, **kwargs: Any) -> str:
        """テンプレートに変数を補間する。

        Args:
            **kwargs: 変数名と値のマッピング

        Returns:
            フォーマット済みの文字列

        Raises:
            ValueError: 必須変数が不足している場合
        """
        # 必須変数のチェック
        required_vars = {var.name for var in self.variables if var.required}
        provided_vars = set(kwargs.keys())
        missing_vars = required_vars - provided_vars

        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")

        # デフォルト値の適用
        format_args = {}
        for var in self.variables:
            if var.name in kwargs:
                format_args[var.name] = kwargs[var.name]
            elif var.default is not None:
                format_args[var.name] = var.default
            elif not var.required:
                format_args[var.name] = ""

        # 追加の変数も含める（定義されていない変数も許可）
        for key, value in kwargs.items():
            if key not in format_args:
                format_args[key] = value

        # テンプレートのフォーマット
        try:
            return self.template.format(**format_args)
        except KeyError as e:
            raise ValueError(f"Variable {e} not found in template") from e

    @classmethod
    def from_yaml(cls, yaml_content: dict[str, Any]) -> "PromptTemplate":
        """YAML形式の辞書からプロンプトテンプレートを作成する。

        Args:
            yaml_content: YAML形式の辞書

        Returns:
            プロンプトテンプレート
        """
        variables = []
        if "variables" in yaml_content:
            for var_data in yaml_content["variables"]:
                variables.append(PromptVariable(**var_data))

        return cls(
            name=yaml_content["name"],
            template=yaml_content["template"],
            variables=variables,
            description=yaml_content.get("description"),
            version=yaml_content.get("version", "1.0.0"),
            metadata=yaml_content.get("metadata", {}),
        )


class PromptTemplateLibrary(BaseModel):
    """プロンプトテンプレートのライブラリを表す値オブジェクト。

    Attributes:
        templates: テンプレート名とテンプレートのマッピング
    """

    templates: dict[str, PromptTemplate] = Field(
        default_factory=dict, description="テンプレート名とテンプレートのマッピング"
    )

    model_config = {"frozen": False}  # テンプレートの追加を許可

    def add_template(self, template: PromptTemplate) -> None:
        """テンプレートを追加する。

        Args:
            template: 追加するテンプレート

        Raises:
            ValueError: 同名のテンプレートが既に存在する場合
        """
        if template.name in self.templates:
            raise ValueError(f"Template '{template.name}' already exists")
        template.validate_variables()
        self.templates[template.name] = template

    def get_template(self, name: str) -> PromptTemplate | None:
        """テンプレートを取得する。

        Args:
            name: テンプレート名

        Returns:
            テンプレート（存在しない場合はNone）
        """
        return self.templates.get(name)

    def format_template(self, name: str, **kwargs: Any) -> str:
        """テンプレートをフォーマットする。

        Args:
            name: テンプレート名
            **kwargs: 変数名と値のマッピング

        Returns:
            フォーマット済みの文字列

        Raises:
            ValueError: テンプレートが存在しない場合
        """
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template '{name}' not found")
        return template.format(**kwargs)
