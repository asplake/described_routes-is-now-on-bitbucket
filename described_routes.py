from template_parser import URITemplate 

class ResourceTemplate(object):
    """
    Dynamic, framework-neutral metadata describing path/URI structures natively in Python and through
    JSON, YAML and XML representations.

    Purpose: to define and support a metadata format capable of being generated dynamically from web
    applications, describing the URI structure of the application in its entirety or of specific resources
    and their related subresources.  In a very lightweight manner - focussed only on resource identification -
    it aims to cover a spectrum ranging from application description languages (cf WSDL and WADL) through to
    more dynamic, hyperlinked interaction (cf REST and HATEOAS).
    """
    def __init__(self, d={}, **kwargs):
        """
        Initialize a ResourceTemplate from a dict &/or keyword arguments, all of which are optional.  For example:

        >>> user_articles = ResourceTemplate(
        ...                     {
        ...                         'name':                'user_articles',
        ...                         'rel':                 'articles',
        ...                         'uri_template':        'http://example.com/users/{user_id}/articles{-prefix|.|format}',
        ...                         'path_template':       '/users/{user_id}/articles{-prefix|.|format}',
        ...                         'params':              ['user_id'],
        ...                         'optional_params':     ['format'],
        ...                         'options':             ['GET', 'POST']
        ...                     },
        ...                     resource_templates = [user_article, new_user_article])

        The resource_templates parameter can be a ResourceTemplates object, an array of ResourceTemplate objects
        or an array of hashes.  This last option makes it easy to initialize a whole hierarchy directly from deserialised JSON or YAML
        objects, e.g.:

        >>> user_articles = ResourceTemplate(JSON.parse(json))
        >>> user_articles = ResourceTemplate(YAML.load(yaml))
        """
        if d:
            if not isinstance(d, dict):
                raise TypeError(repr(d) + " is not a dict")
            if kwargs:
                d = d.clone
                d.update(kwargs)
        else:
            d = kwargs

        for attr in ('name', 'rel', 'uri_template', 'path_template'):
            setattr(self, attr, d.get(attr))
        
        for attr in ('params', 'optional_params', 'options'):
            setattr(self, attr, d.get(attr, []))

        self.resource_templates = ResourceTemplates(d.get('resource_templates', []))

    def to_dict(self, base=None):
        """
        Convert to a dict, perhaps for a further conversion to JSON or YAML.
        """
        d = dict()
        
        for attr in ('name', 'rel', 'uri_template', 'path_template'):
            val = getattr(self, attr)
            if val: d['attr'] = val

        if self.resource_templates: d['resource_templates'] = self.resource_templates.to_list()
        
        return d

    def __str__(self):
        """
        Text report
        """
        return str(ResourceTemplates([self]))


    def positional_params(self, parent):
        """
        Returns params and any optional_params in order, removing the supplied parent's params
        """
        
        all_params = self.params + self.optional_params
        if parent:
            return [p for p in all_params if p not in parent.params]
        else:
            return all_params


    def uri_template_for_base(self, base):
        """
        Returns this template's URI template or one constructed from the given base and path template.
        """
        if self.uri_template:
            return self.uri_template
        elif base and self.path_template:
            return base + self.path_template
            
    def uri_for(self, actual_params, base=None):
        """
        Returns an expanded URI template with template variables filled from the given params hash.
        Raises KeyError if params doesn't contain all mandatory params.
        """
        missing_params = [p for p in self.params if p not in actual_params]
        if missing_params:
            raise KeyError('missing params ' + ', '.join(missing_params))
            
        t = self.uri_template_for_base(base)
        if not t:
            raise RuntimeError('uri_template_for_base(%s) is None; path_template=%s' % (repr(base), repr(self.path_template)))
        
        return URITemplate(t).sub(actual_params)
        
    def path_for(self, actual_params):
        """
        Returns an expanded path template with template variables filled from the given params hash.
        Raises KeyError if params doesn't contain all mandatory params.
        """
        missing_params = [p for p in self.params if p not in actual_params]
        if missing_params:
            raise KeyError('missing params ' + ', '.join(missing_params))

        if not self.path_template:
            raise RuntimeError('path_template is None')

        return URITemplate(self.path_template).sub(actual_params)
    
    def partial_expand(self, actual_params):
        """
        Return a new resource template with the path_template &/or uri_template partially expanded with the given params        
        """
        return type(self)(
                    name               = self.name,
                    rel                = self.rel,
                    uri_template       = self.partial_expand_uri_template(self.uri_template,  actual_params),
                    path_template      = self.partial_expand_uri_template(self.path_template, actual_params),
                    params             = [p for p in self.params if p not in actual_params],
                    optional_params    = [p for p in self.optional_params if p not in actual_params],
                    options            = self.options,
                    resource_templates = self.resource_templates.partial_expand(actual_params))

    def partial_expand_uri_template(self, ut, actual_params):
        """
        Partially expand a URI template
        """
        # TODO implement URITemplate.partial_expand
        if ut: return URITemplate(ut).sub(actual_params)
  
    def find_by_rel(self, rel):
        """
        Find member ResourceTemplate objects with the given rel
        """
        return [t for t in self.resource_templates if t.rel == rel]


"""
A list of ResourceTemplate objects.
"""
class ResourceTemplates(list):
    def __init__(self, collection=[]):
        """
        Initialize a ResourceTemplates object (a new collection of ResourceTemplate objects) from given collection of
        ResourceTemplates or hashes
        """
        super(ResourceTemplates, self).__init__()
        if collection:
            for rt in collection:
                if isinstance(rt, ResourceTemplate):
                    self.append(rt)
                elif isinstance(rt, dict):
                    self.append(ResourceTemplate(rt))
                else:
                    raise TypeError(repr(rt) + " is neither a ResourceTemplate nor a dict")

    def to_list(self):
        """
        Convert member ResourceTemplate objects to array of hashes equivalent to their JSON or YAML representations
        """
        return [t.to_dict() for t in self]
        
    def all_by_name(self, d = None):
        """
        Get a dict of all named ResourceTemplate objects contained in the supplied collection, keyed by name
        """
        if d is None:
            d = {}
        
        for rt in self:
            if rt.name:
                d[rt.name] = rt
            rt.resource_templates.all_by_name(d)
        
        return d

    def to_table(self, parent_template=None, table=None, indent=''):
        """
        For to_text()
        """
        if table is None:
            table = []
        
        for rt in self:
            if parent_template:
                link = rt.rel or ''
                new_params = [p for p in rt.params if p not in parent_template.params]
            else:
                link = rt.name
                new_params = rt.params
            table.append([
                indent + link + ', '.join(['{' + p + '}' for p in new_params]),
                rt.name or '',
                ', '.join(rt.options),
                rt.uri_template or rt.path_template])
            rt.resource_templates.to_table(rt,  table, indent + '  ')

        return table

    def __str__(self):
        """
        Text report
        """
        table = self.to_table()
        
        for col in range(3):
            col_width = max([len(row[col]) for row in table])
            for row in table:
                row[col] = row[col].ljust(col_width)
        
        return '\n'.join([' '.join(row) for row in table] + [''])
        
    def partial_expand(self, actual_params):
        """
        Partially expand the path_template or uri_template of the given resource templates with the given params,
        returning new resource templates
        """
        type(self)([rt.partial_expand(actual_params) for rt in self])


if __name__ == "__main__":

    users = ResourceTemplate(
        {
            'name':               'users',
            'uri_template':       'http://example.com/users{-prefix|.|format}',
            'path_template':      '/users{-prefix|.|format}',
            'optional_params':    ['format'],
            'options':            ['GET', 'POST'],
            'resource_templates': [
                {
                    'name':               'user',
                    'uri_template':       'http://example.com/users/{user_id}{-prefix|.|format}',
                    'path_template':      '/users/{user_id}{-prefix|.|format}',
                    'params':             ['user_id'],
                    'optional_params':    ['format'],
                    'options':            ['GET', 'PUT', 'DELETE'],
                    'resource_templates': [
                        {
                            'name':            'user_articles',
                            'rel':             'articles',
                            'uri_template':    'http://example.com/users/{user_id}/articles{-prefix|.|format}',
                            'path_template':   '/users/{user_id}/articles{-prefix|.|format}',
                            'params':          ['user_id'],
                            'optional_params': ['format'],
                            'options':         ['GET', 'POST']
                        },
                        {
                            'name':            'edit_user',
                            'rel':             'edit',
                            'uri_template':    'http://example.com/users/{user_id}/edit{-prefix|.|format}',
                            'path_template':   '/users/{user_id}/edit{-prefix|.|format}',
                            'params':          ['user_id'],
                            'optional_params': ['format'],
                            'options':         ['GET']
                        }
                    ]
                }
            ]
        })

    dojo = {'user_id': 'dojo'}

    resource_templates = ResourceTemplates([users])
    
    user = resource_templates.all_by_name()['user']
    user_articles = resource_templates.all_by_name()['user_articles']
    edit_user = user.find_by_rel('edit')[0]

    print '\n', users, '\n', users.to_dict(), '\n', users.path_for({})
    print '\n', user_articles, '\n', user_articles.to_dict(), '\n', user_articles.path_for(dojo)

    user_dojo = user.partial_expand(dojo)
    print '\n', user_dojo, '\n', user_dojo.to_dict(), '\n', user_dojo.path_for(dojo)

    print "\nuser.find_by_rel('edit')[0]\n", user.find_by_rel('edit')[0]

    print "\nresource_templates.all_by_name()['user_articles']\n", resource_templates.all_by_name()['user_articles']

    import json
    print json.dumps(resource_templates.to_list(), sort_keys=True, indent=4)
