def Field(default=None, default_factory=None, **kwargs):
    return default_factory() if default_factory else default
class BaseModel:
    def __init__(self, **data):
        anns={}
        for c in reversed(self.__class__.mro()): anns.update(getattr(c,'__annotations__',{}))
        for k,v in self.__class__.__dict__.items():
            if not k.startswith('_') and k in anns and k not in data: setattr(self,k,v)
        for k in anns:
            if k in data: setattr(self,k,data[k])
        for k,v in data.items():
            if not hasattr(self,k): setattr(self,k,v)
    @classmethod
    def model_validate(cls, data):
        anns=getattr(cls,'__annotations__',{})
        kwargs={}
        for k,v in data.items():
            if k=='sections' and cls.__name__=='Template':
                from linesheet_builder.models import TemplateSection
                v=[TemplateSection.model_validate(x) for x in v]
            if k=='questions' and cls.__name__=='TemplateSection':
                from linesheet_builder.models import TemplateQuestion
                v=[TemplateQuestion.model_validate(x) for x in v]
            kwargs[k]=v
        return cls(**kwargs)
    def model_dump(self): return dict(self.__dict__)
